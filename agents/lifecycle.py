"""Agent lifecycle — state machine and heartbeat for browser agents.

State machine: IDLE -> ASSIGNED -> BROWSING -> REPORTING -> IDLE

Each agent emits AGENT_UPDATE events on Redis for the War Room UI,
and maintains a heartbeat key with TTL while BROWSING.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# Heartbeat interval and TTL
HEARTBEAT_INTERVAL_S = 30
HEARTBEAT_TTL_S = 60

# Valid state transitions
_TRANSITIONS: dict[str, set[str]] = {
    "IDLE": {"ASSIGNED"},
    "ASSIGNED": {"BROWSING", "IDLE"},  # IDLE for cancel/error
    "BROWSING": {"REPORTING", "IDLE"},  # IDLE for timeout/crash
    "REPORTING": {"IDLE"},
}


class AgentLifecycle:
    """Manages the lifecycle of a single browser agent.

    Tracks state transitions, emits AGENT_UPDATE events via Redis,
    and runs a heartbeat loop while the agent is BROWSING.

    Usage:
        lifecycle = AgentLifecycle("agent_0", redis, mission_id)
        await lifecycle.transition("ASSIGNED", task_id=task_id)
        await lifecycle.transition("BROWSING", site_url="https://...")
        # ... agent does work ...
        await lifecycle.transition("REPORTING")
        # ... evidence emission ...
        await lifecycle.transition("IDLE")
    """

    def __init__(
        self,
        agent_id: str,
        redis: Any,
        mission_id: str | UUID,
    ) -> None:
        self.agent_id = agent_id
        self._redis = redis
        self._mission_id = str(mission_id)
        self._status = "IDLE"
        self._task_id: str | None = None
        self._heartbeat_task: asyncio.Task | None = None

    @property
    def status(self) -> str:
        return self._status

    async def transition(
        self,
        new_status: str,
        *,
        task_id: str | UUID | None = None,
        site_url: str | None = None,
        agent_type: str | None = None,
    ) -> None:
        """Transition the agent to a new state.

        Args:
            new_status: Target status.
            task_id: Task UUID (set on ASSIGNED).
            site_url: URL being browsed (set on BROWSING).
            agent_type: Agent type like OFFICIAL_SITE (set on ASSIGNED).

        Raises:
            ValueError: If the transition is not valid.
        """
        allowed = _TRANSITIONS.get(self._status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {self._status} -> {new_status} "
                f"(allowed: {allowed})"
            )

        old_status = self._status
        self._status = new_status

        if task_id is not None:
            self._task_id = str(task_id)

        # Manage heartbeat
        if new_status == "BROWSING":
            self._start_heartbeat()
        elif old_status == "BROWSING":
            self._stop_heartbeat()

        # Update Redis agent state
        from agents.pool import agent_key

        mapping: dict[str, str] = {
            "status": new_status,
            "last_heartbeat": str(time.time()),
        }
        if task_id is not None:
            mapping["task_id"] = str(task_id)
        if agent_type is not None:
            mapping["agent_type"] = agent_type

        await self._redis.hset(agent_key(self.agent_id), mapping=mapping)

        # Clear fields on IDLE
        if new_status == "IDLE":
            await self._redis.hset(
                agent_key(self.agent_id),
                mapping={
                    "task_id": "",
                    "mission_id": "",
                    "agent_type": "",
                    "session_id": "",
                },
            )
            self._task_id = None

        # Publish AGENT_UPDATE event for the War Room UI
        await self._publish_agent_update(site_url=site_url)

        logger.info(
            "Agent %s: %s -> %s (task=%s)",
            self.agent_id,
            old_status,
            new_status,
            self._task_id,
        )

    async def _publish_agent_update(self, site_url: str | None = None) -> None:
        """Emit an AGENT_UPDATE event on the mission's Redis channel."""
        try:
            from streaming.channels import publish_agent_update

            agent_state = {
                "id": self.agent_id,
                "status": self._status,
                "task_id": self._task_id or "",
                "site_url": site_url or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await publish_agent_update(self._redis, self._mission_id, agent_state)
        except Exception as exc:
            logger.warning(
                "Failed to publish AGENT_UPDATE for %s: %s", self.agent_id, exc
            )

    # -- Heartbeat -------------------------------------------------------------

    def _start_heartbeat(self) -> None:
        """Start the heartbeat background task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.debug("Heartbeat started for %s", self.agent_id)

    def _stop_heartbeat(self) -> None:
        """Stop the heartbeat background task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        logger.debug("Heartbeat stopped for %s", self.agent_id)

    async def _heartbeat_loop(self) -> None:
        """Send heartbeat pings to Redis with TTL."""
        hb_key = f"agent:{self.agent_id}:heartbeat"
        try:
            while True:
                await self._redis.set(hb_key, "alive", ex=HEARTBEAT_TTL_S)
                await asyncio.sleep(HEARTBEAT_INTERVAL_S)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("Heartbeat error for %s: %s", self.agent_id, exc)


async def run_agent_task(
    agent_id: str,
    redis: Any,
    mission_id: str | UUID,
    task_id: str | UUID,
    objective: str,
    agent_type: str,
    constraints: dict[str, Any] | None = None,
    backend_url: str = "http://localhost:8000",
) -> None:
    """Execute a full agent lifecycle: ASSIGNED -> BROWSING -> REPORTING -> IDLE.

    This is the main entry point called by the command channel handler.

    Args:
        agent_id: Agent ID (e.g., "agent_0").
        redis: aioredis client.
        mission_id: Mission UUID.
        task_id: Task UUID.
        objective: Research task description.
        agent_type: Agent type (e.g., OFFICIAL_SITE).
        constraints: Optional task constraints.
        backend_url: Backend API base URL.
    """
    lifecycle = AgentLifecycle(agent_id, redis, str(mission_id))
    # The agent was already claimed (ASSIGNED) by pool.claim_agent() before
    # this function is called. Sync the lifecycle's internal state to match.
    lifecycle._status = "ASSIGNED"

    try:
        # Load agent prompt
        try:
            from agents.prompts import load_prompt

            agent_prompt = load_prompt(agent_type)
        except FileNotFoundError:
            logger.warning("No prompt for agent type %s, using default", agent_type)
            agent_prompt = f"You are a research agent of type {agent_type}. Research the given objective thoroughly."

        # ASSIGNED -> BROWSING
        await lifecycle.transition("BROWSING", task_id=task_id, agent_type=agent_type)

        # Run browser task
        from agents.browser_session import run_browser_task

        result = await run_browser_task(objective, agent_prompt, constraints)

        # BROWSING -> REPORTING
        await lifecycle.transition("REPORTING")

        # Emit evidence
        from agents.evidence_emitter import emit_findings

        await emit_findings(result, mission_id, agent_id, task_id, backend_url)

        # Emit TASK_COMPLETE signal
        await redis.lpush(
            f"agent:{agent_id}:findings",
            json.dumps({"type": "TASK_COMPLETE", "task_id": str(task_id)}),
        )

    except Exception as exc:
        logger.error("Agent %s task failed: %s", agent_id, exc)
    finally:
        # REPORTING -> IDLE (or error recovery -> IDLE)
        try:
            if lifecycle.status != "IDLE":
                # Force back to IDLE via valid path
                if lifecycle.status == "BROWSING":
                    await lifecycle.transition("REPORTING")
                if lifecycle.status in ("REPORTING", "ASSIGNED"):
                    await lifecycle.transition("IDLE")
        except Exception:
            # Last resort: directly set IDLE in Redis
            from agents.pool import release_agent

            await release_agent(redis, agent_id)
