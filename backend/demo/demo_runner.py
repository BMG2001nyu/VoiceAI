"""Demo-mode agent runner — simulates browser agents using mock evidence.

When DEMO_MODE=true, the planning loop spawns these lightweight coroutines
instead of real browser agents. Each coroutine:

1. Publishes an AGENT_UPDATE (BROWSING) event.
2. Sleeps 2-4 seconds to simulate browsing.
3. Picks a mock evidence item from demo/mock_evidence.json.
4. Inserts it into Postgres via the evidence repository.
5. Publishes EVIDENCE_FOUND + TIMELINE_EVENT events to Redis.
6. Transitions through REPORTING → IDLE with appropriate delays.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

# Resolve the mock evidence file relative to the repo root.
_MOCK_EVIDENCE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "demo" / "mock_evidence.json"
)

_mock_evidence_cache: list[dict[str, Any]] | None = None

# Default site URLs per agent for UI display
_AGENT_SITE_URLS: dict[str, str] = {
    "agent_0": "company-website.com",
    "agent_1": "techcrunch.com",
    "agent_2": "reddit.com/r/technology",
    "agent_3": "github.com",
    "agent_4": "crunchbase.com",
    "agent_5": "news.google.com",
}


def _agent_site_url(agent_id: str) -> str:
    """Return a representative site URL for an agent."""
    return _AGENT_SITE_URLS.get(agent_id, "web-search.ai")


def _load_mock_evidence() -> list[dict[str, Any]]:
    """Load and cache mock evidence from the JSON file."""
    global _mock_evidence_cache
    if _mock_evidence_cache is not None:
        return _mock_evidence_cache

    try:
        raw = _MOCK_EVIDENCE_PATH.read_text(encoding="utf-8")
        _mock_evidence_cache = json.loads(raw)
    except Exception as exc:
        logger.error("Failed to load mock evidence from %s: %s", _MOCK_EVIDENCE_PATH, exc)
        _mock_evidence_cache = []

    return _mock_evidence_cache


async def run_demo_agent(
    agent_id: str,
    task_description: str,
    mission_id: str,
    db: asyncpg.Pool,
    redis: Any,
) -> None:
    """Simulate a single browser-agent task cycle in demo mode.

    Args:
        agent_id: The agent performing the task (e.g. "agent_0").
        task_description: Human-readable task objective.
        mission_id: UUID of the mission.
        db: asyncpg connection pool.
        redis: Redis client.
    """
    from agents.pool import update_agent_status
    from streaming.channels import (
        publish_agent_update,
        publish_timeline_event,
        publish,
    )
    from evidence.repository import insert_evidence
    from evidence.scoring import compute_confidence

    now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

    # Derive a site_url from the agent_id for UI display
    site_url = _agent_site_url(agent_id)

    try:
        # ── 0. ASSIGNED ───────────────────────────────────────────────────
        await update_agent_status(redis, agent_id, "ASSIGNED")
        await publish_agent_update(
            redis,
            mission_id,
            {
                "agent_id": agent_id,
                "status": "ASSIGNED",
                "objective": task_description,
                "site_url": site_url,
                "timestamp": now_iso(),
            },
        )
        await publish_timeline_event(
            redis,
            mission_id,
            {
                "id": str(uuid.uuid4()),
                "type": "agent_assigned",
                "description": f"{agent_id} assigned: {task_description[:80]}",
                "timestamp": now_iso(),
                "payload": {"agent_id": agent_id},
            },
        )
        await asyncio.sleep(random.uniform(1.0, 2.0))

        # ── 1. BROWSING ──────────────────────────────────────────────────
        await update_agent_status(redis, agent_id, "BROWSING")
        await publish_agent_update(
            redis,
            mission_id,
            {
                "agent_id": agent_id,
                "status": "BROWSING",
                "objective": task_description,
                "site_url": site_url,
                "timestamp": now_iso(),
            },
        )
        await publish_timeline_event(
            redis,
            mission_id,
            {
                "id": str(uuid.uuid4()),
                "type": "agent_browsing",
                "description": f"{agent_id} started browsing: {task_description[:80]}",
                "timestamp": now_iso(),
                "payload": {"agent_id": agent_id},
            },
        )

        # ── 2. Simulate browsing delay ───────────────────────────────────
        await asyncio.sleep(random.uniform(4.0, 8.0))

        # ── 3. Pick mock evidence ────────────────────────────────────────
        mock_items = _load_mock_evidence()
        if not mock_items:
            logger.warning("No mock evidence available for %s", agent_id)
            await _release(
                redis, agent_id, mission_id, publish_agent_update, now_iso,
                task_description=task_description, site_url=site_url,
            )
            return

        # Prefer evidence matching this agent_id, fall back to random.
        matching = [e for e in mock_items if e.get("agent_id") == agent_id]
        evidence_template = random.choice(matching) if matching else random.choice(mock_items)

        # ── 4. Insert evidence into DB ───────────────────────────────────
        confidence = compute_confidence(
            evidence_template.get("source_url", ""),
            evidence_template.get("snippet", ""),
        )

        row = await insert_evidence(
            db,
            mission_id=mission_id,
            agent_id=agent_id,
            claim=evidence_template["claim"],
            summary=evidence_template.get("summary", ""),
            source_url=evidence_template.get("source_url", "https://example.com"),
            snippet=evidence_template.get("snippet", ""),
            confidence=confidence,
            novelty=round(random.uniform(0.5, 1.0), 2),
            theme=evidence_template.get("theme"),
        )

        # ── 5. Publish EVIDENCE_FOUND ────────────────────────────────────
        payload = dict(row)
        ts_iso = payload["timestamp"].isoformat()
        payload["timestamp"] = ts_iso
        payload["created_at"] = ts_iso
        await publish(redis, mission_id, "EVIDENCE_FOUND", payload)

        # ── 6. Publish TIMELINE_EVENT ────────────────────────────────────
        await publish_timeline_event(
            redis,
            mission_id,
            {
                "id": str(uuid.uuid4()),
                "type": "evidence_found",
                "description": (
                    f"{agent_id} found evidence: {evidence_template['claim'][:60]}"
                ),
                "timestamp": now_iso(),
                "payload": {
                    "agent_id": agent_id,
                    "evidence_id": row["id"],
                    "theme": evidence_template.get("theme", ""),
                },
            },
        )

        logger.info(
            "Demo agent %s produced evidence %s for mission %s",
            agent_id,
            row["id"],
            mission_id[:8],
        )

        # ── 7. REPORTING ─────────────────────────────────────────────────
        await update_agent_status(redis, agent_id, "REPORTING")
        await publish_agent_update(
            redis,
            mission_id,
            {
                "agent_id": agent_id,
                "status": "REPORTING",
                "objective": task_description,
                "site_url": site_url,
                "timestamp": now_iso(),
            },
        )
        await asyncio.sleep(random.uniform(2.0, 3.0))

    except asyncio.CancelledError:
        logger.info("Demo agent %s cancelled", agent_id)
        raise
    except Exception:
        logger.exception("Demo agent %s error", agent_id)
    finally:
        # ── 8. IDLE ──────────────────────────────────────────────────────
        await _release(
            redis, agent_id, mission_id, publish_agent_update, now_iso,
            task_description=task_description, site_url=site_url,
        )


async def _release(
    redis: Any,
    agent_id: str,
    mission_id: str,
    publish_agent_update: Any,
    now_iso: Any,
    task_description: str = "",
    site_url: str = "",
) -> None:
    """Release the agent back to IDLE and publish the update."""
    from agents.pool import release_agent

    try:
        await release_agent(redis, agent_id)
        await publish_agent_update(
            redis,
            mission_id,
            {
                "agent_id": agent_id,
                "status": "IDLE",
                "objective": task_description,
                "site_url": site_url,
                "timestamp": now_iso(),
            },
        )
    except Exception:
        logger.exception("Failed to release demo agent %s", agent_id)


async def run_demo_agents_batch(
    assignments: list,
    mission_id: str,
    db: asyncpg.Pool,
    redis: Any,
) -> list[asyncio.Task]:
    """Spawn demo-agent tasks for a batch of assignments.

    Args:
        assignments: List of AssignAction objects from the assignment algorithm.
        mission_id: UUID of the mission.
        db: asyncpg connection pool.
        redis: Redis client.

    Returns:
        List of asyncio.Task handles (caller can await or cancel).
    """
    tasks: list[asyncio.Task] = []
    for action in assignments:
        task = asyncio.create_task(
            run_demo_agent(
                agent_id=action.agent_id,
                task_description=action.objective,
                mission_id=mission_id,
                db=db,
                redis=redis,
            ),
            name=f"demo:{action.agent_id}:{mission_id[:8]}",
        )
        tasks.append(task)

    if tasks:
        logger.info(
            "Spawned %d demo agents for mission %s",
            len(tasks),
            mission_id[:8],
        )

    return tasks
