"""Nova 2 Lite client — orchestrator brain for Mission Control.

Uses the OpenAI-compatible Nova API (api.nova.amazon.com) for:
  - Task graph construction: decompose a mission objective into TaskNodes
  - Planning loop: given a MissionContextPacket, return AgentCommands
  - Generic async chat with optional tool calling and streaming

Rate limits (free tier): 20 RPM / 500 RPD.
Tenacity retries handle transient 429s automatically.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any, AsyncIterator

from openai import AsyncOpenAI, APIStatusError, APIConnectionError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NOVA_API_BASE = "https://api.nova.amazon.com/v1"
DEFAULT_MODEL = "nova-2-lite-v1"

AGENT_TYPES = {
    "OFFICIAL_SITE",
    "NEWS_BLOG",
    "REDDIT_HN",
    "GITHUB",
    "FINANCIAL",
    "RECENT_NEWS",
}

COMMAND_TYPES = {"ASSIGN", "REDIRECT", "STOP"}

# System prompt used for every orchestrator planning call
_ORCHESTRATOR_SYSTEM = """\
You are the Mission Orchestrator for Mission Control, a real-time AI intelligence system.
Your job is to plan the next actions for a fleet of browser agents gathering evidence for a mission.

Rules:
- Be decisive and efficient. Return only the JSON asked for — no prose, no markdown fences.
- Prefer assigning idle agents before redirecting active ones.
- Only STOP an agent when its task is clearly complete or redundant.
- Prioritise tasks with the highest information value and least duplication of existing evidence.
"""

# System prompt for task decomposition
_DECOMPOSER_SYSTEM = """\
You are a research planning assistant for an AI intelligence system.
Given a mission objective, decompose it into a flat list of parallel research tasks,
one per agent type. Each task should be focused, achievable in under 60 seconds of browsing,
and use a different information source.

Return ONLY a JSON array — no markdown, no explanation.
"""


# ---------------------------------------------------------------------------
# Retry decorator — shared across all API call methods
# ---------------------------------------------------------------------------

_retry_on_transient = retry(
    retry=retry_if_exception_type((APIStatusError, APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> Any:
    """Extract the first JSON value from a model response.

    Strips markdown code fences (```json ... ```) if present,
    then parses the result. Raises ValueError if no valid JSON found.
    """
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()

    # Try full string first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fall back to extracting the first balanced [...] or {...} block
    for opener, closer in [("[", "]"), ("{", "}")]:
        start = cleaned.find(opener)
        if start == -1:
            continue
        depth = 0
        for i, ch in enumerate(cleaned[start:], start):
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"No valid JSON found in model response: {text[:300]!r}")


def _validate_task_nodes(raw: list[dict]) -> list[dict]:
    """Coerce and validate raw task node dicts from the model."""
    validated = []
    for item in raw:
        agent_type = str(item.get("agent_type", "")).upper()
        if agent_type not in AGENT_TYPES:
            logger.warning("Unknown agent_type %r — skipping task node", agent_type)
            continue
        validated.append(
            {
                "description": str(item.get("description", "")).strip(),
                "agent_type": agent_type,
                "priority": max(1, min(10, int(item.get("priority", 5)))),
                "dependencies": [str(d) for d in item.get("dependencies", [])],
            }
        )
    return validated


def _validate_agent_commands(raw: list[dict]) -> list[dict]:
    """Coerce and validate raw agent command dicts from the model."""
    validated = []
    for item in raw:
        command_type = str(item.get("command_type", "")).upper()
        if command_type not in COMMAND_TYPES:
            logger.warning("Unknown command_type %r — skipping command", command_type)
            continue
        validated.append(
            {
                "command_type": command_type,
                "agent_id": str(item.get("agent_id", "")),
                "task_id": item.get("task_id"),
                "objective": str(item.get("objective", "")).strip(),
                "constraints": item.get("constraints"),
            }
        )
    return validated


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class LiteClient:
    """Async Nova 2 Lite client via the OpenAI-compatible Nova API.

    Usage::

        client = LiteClient(api_key="...")
        tasks = await client.plan_tasks("Pitch to Sequoia next week...")
        commands = await client.plan_next_actions(context_packet)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        if api_key is None:
            # Lazy import to avoid circular dependency at module load time
            try:
                from backend.config import settings  # type: ignore[import]

                api_key = settings.nova_api_key or None
            except Exception:
                pass

        if not api_key:
            import os

            api_key = os.environ.get("NOVA_API_KEY", "")

        if not api_key:
            raise ValueError(
                "Nova API key is required. Set NOVA_API_KEY env var or pass api_key=."
            )

        self._model = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=NOVA_API_BASE,
        )

    # ------------------------------------------------------------------
    # Core chat primitive
    # ------------------------------------------------------------------

    @_retry_on_transient
    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        reasoning_effort: str | None = None,
    ) -> str:
        """Send a chat completion and return the assistant text response.

        Args:
            messages: Conversation history in OpenAI message format.
            system: Optional system prompt prepended to messages.
            tools: Optional list of tool definitions (OpenAI function schema).
            tool_choice: Tool selection strategy ("auto", "none", or specific tool).
            temperature: Sampling temperature (lower = more deterministic).
            max_tokens: Maximum tokens to generate.
            reasoning_effort: Optional reasoning level ("low", "medium", "high").

        Returns:
            The assistant's text content string.

        Raises:
            APIStatusError: On non-retryable HTTP errors (4xx other than 429).
            ValueError: If the response contains no text content.
        """
        full_messages: list[dict[str, Any]] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        kwargs: dict[str, Any] = dict(
            model=self._model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort

        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Nova Lite returned an empty response")
        return content

    @_retry_on_transient
    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream text chunks from a chat completion.

        Yields individual text delta strings as they arrive.
        Use this for streaming briefing narration or real-time feedback.

        Example::

            async for chunk in client.stream_chat(messages):
                print(chunk, end="", flush=True)
        """
        full_messages: list[dict[str, Any]] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    # ------------------------------------------------------------------
    # High-level orchestrator methods
    # ------------------------------------------------------------------

    async def plan_tasks(
        self,
        objective: str,
        *,
        max_tasks: int = 6,
    ) -> list[dict[str, Any]]:
        """Decompose a mission objective into a flat list of TaskNode dicts.

        Calls Nova Lite with a structured prompt and parses the JSON output.
        Each returned dict matches the TaskNode schema:
            description, agent_type, priority, dependencies

        Args:
            objective: The raw mission objective string from the user.
            max_tasks: Maximum number of tasks to request (default 6).

        Returns:
            List of validated TaskNode dicts ready to insert into the DB.

        Raises:
            ValueError: If the model returns invalid or unparseable JSON.
        """
        prompt = (
            f"Mission objective: {objective}\n\n"
            f"Decompose this into up to {max_tasks} parallel research tasks, "
            f"one per relevant agent type. Use only these agent types: "
            f"{', '.join(sorted(AGENT_TYPES))}.\n\n"
            "Return a JSON array of task objects with these exact keys:\n"
            "  description (string) — what the agent should research\n"
            "  agent_type (string)  — one of the types above\n"
            "  priority (int 1–10)  — higher = do sooner\n"
            "  dependencies (array) — empty [] for parallel tasks\n\n"
            "Example output:\n"
            '[\n  {"description": "Scrape sequoiacap.com for partners and portfolio", '
            '"agent_type": "OFFICIAL_SITE", "priority": 9, "dependencies": []}\n]'
        )

        raw_text = await self.chat(
            messages=[{"role": "user", "content": prompt}],
            system=_DECOMPOSER_SYSTEM,
            temperature=0.1,
            max_tokens=1024,
        )

        try:
            raw = _extract_json(raw_text)
        except ValueError as exc:
            raise ValueError(
                f"plan_tasks: failed to parse JSON from Nova Lite.\n"
                f"Objective: {objective!r}\nResponse: {raw_text!r}"
            ) from exc

        if not isinstance(raw, list):
            raise ValueError(
                f"plan_tasks: expected a JSON array, got {type(raw).__name__}"
            )

        tasks = _validate_task_nodes(raw)
        logger.info("plan_tasks produced %d tasks for objective %r", len(tasks), objective[:60])
        return tasks

    async def plan_next_actions(
        self,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Given a MissionContextPacket, return a list of AgentCommand dicts.

        Called by the orchestrator planning loop each cycle to decide
        which agents to assign, redirect, or stop.

        Args:
            context: A MissionContextPacket dict (see tasks.md Data Schemas).

        Returns:
            List of validated AgentCommand dicts:
                command_type, agent_id, task_id, objective, constraints

        Raises:
            ValueError: If the model returns invalid JSON.
        """
        context_json = json.dumps(context, indent=2)

        prompt = (
            "Current mission context:\n"
            f"```json\n{context_json}\n```\n\n"
            "Based on this context, decide the next actions for the agent fleet.\n"
            "Return a JSON array of AgentCommand objects with these exact keys:\n"
            "  command_type (string) — one of: ASSIGN, REDIRECT, STOP\n"
            "  agent_id     (string) — target agent ID\n"
            "  task_id      (string|null) — for ASSIGN: the task UUID to execute\n"
            "  objective    (string) — natural language objective for the agent\n"
            "  constraints  (object|null) — optional: {max_depth, allowed_domains, time_limit_sec}\n\n"
            "Return an empty array [] if no actions are needed this cycle."
        )

        raw_text = await self.chat(
            messages=[{"role": "user", "content": prompt}],
            system=_ORCHESTRATOR_SYSTEM,
            temperature=0.1,
            max_tokens=1024,
            reasoning_effort="medium",
        )

        try:
            raw = _extract_json(raw_text)
        except ValueError as exc:
            raise ValueError(
                f"plan_next_actions: failed to parse JSON from Nova Lite.\n"
                f"Response: {raw_text!r}"
            ) from exc

        if not isinstance(raw, list):
            raise ValueError(
                f"plan_next_actions: expected a JSON array, got {type(raw).__name__}"
            )

        commands = _validate_agent_commands(raw)
        logger.info(
            "plan_next_actions for mission %s → %d commands",
            context.get("mission_id", "?"),
            len(commands),
        )
        return commands

    async def synthesize_briefing(
        self,
        objective: str,
        findings: list[dict[str, Any]],
        *,
        max_tokens: int = 1500,
    ) -> str:
        """Synthesize a spoken intelligence briefing from gathered evidence.

        Produces a concise, voice-ready briefing (2–3 paragraphs) from the
        top findings collected during the mission.

        Args:
            objective: The original mission objective.
            findings: List of EvidenceRecord dicts (claim, summary, source_url, confidence).
            max_tokens: Maximum length of the briefing.

        Returns:
            Briefing text string, ready to pass to Nova Sonic for TTS delivery.
        """
        findings_text = "\n".join(
            f"- [{f.get('theme', 'general')}] {f.get('claim', '')} "
            f"(confidence {f.get('confidence', 0):.0%}, source: {f.get('source_url', 'unknown')})"
            for f in findings[:15]
        )

        prompt = (
            f"Mission: {objective}\n\n"
            f"Gathered evidence:\n{findings_text}\n\n"
            "Write a concise intelligence briefing (2–3 paragraphs, under 200 words) "
            "suitable for spoken delivery. Be direct, specific, and actionable. "
            "Lead with the most important finding. End with key risks or open questions."
        )

        return await self.chat(
            messages=[{"role": "user", "content": prompt}],
            system="You are an elite intelligence analyst delivering a spoken briefing. "
            "Be crisp, factual, and voice-friendly — no bullet points, no markdown.",
            temperature=0.4,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Model info
    # ------------------------------------------------------------------

    @property
    def model(self) -> str:
        """The Nova model ID in use."""
        return self._model

    async def list_models(self) -> list[dict[str, Any]]:
        """Return available models from the Nova API."""
        models = await self._client.models.list()
        return [{"id": m.id, "owned_by": getattr(m, "owned_by", "")} for m in models.data]


# ---------------------------------------------------------------------------
# Module-level singleton factory
# ---------------------------------------------------------------------------


def get_lite_client(api_key: str | None = None) -> LiteClient:
    """Return a LiteClient instance, reading NOVA_API_KEY from env if not provided."""
    return LiteClient(api_key=api_key)


# ---------------------------------------------------------------------------
# Quick smoke test — run directly: python models/lite_client.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    import os

    async def _smoke_test() -> None:
        api_key = os.environ.get("NOVA_API_KEY")
        if not api_key:
            print("Set NOVA_API_KEY to run the smoke test.")
            sys.exit(1)

        client = LiteClient(api_key=api_key)
        print(f"Model: {client.model}")
        print("─" * 50)

        # Test 1: basic chat
        print("Test 1 — basic chat:")
        reply = await client.chat(
            messages=[{"role": "user", "content": "Reply with exactly: LITE_OK"}]
        )
        print(f"  Response: {reply.strip()}")
        assert "LITE_OK" in reply, f"Unexpected response: {reply}"
        print("  ✓ PASSED")

        # Test 2: task decomposition
        print("\nTest 2 — plan_tasks:")
        tasks = await client.plan_tasks(
            "Pitch to Sequoia next week. Find their recent investments and AI portfolio."
        )
        print(f"  Produced {len(tasks)} tasks:")
        for t in tasks:
            print(f"    [{t['agent_type']:15s}] p={t['priority']} — {t['description'][:60]}")
        assert len(tasks) > 0, "Expected at least one task"
        print("  ✓ PASSED")

        # Test 3: streaming
        print("\nTest 3 — stream_chat:")
        chunks = []
        async for chunk in client.stream_chat(
            messages=[{"role": "user", "content": "Count to 3, one word per line."}]
        ):
            chunks.append(chunk)
        print(f"  Received {len(chunks)} chunks: {''.join(chunks)[:80]!r}")
        assert chunks, "Expected streaming chunks"
        print("  ✓ PASSED")

        print("\n✅ All smoke tests passed.")

    asyncio.run(_smoke_test())
