"""Context packet builder for the orchestrator planning loop.

Assembles all mission state into a single dict that can be serialized
to JSON and passed to Nova Lite's plan_next_actions() method.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import asyncpg
from redis.asyncio import Redis

from agents.pool import get_pool_summary, get_agent_state, agent_ids
from evidence.repository import list_evidence
from missions.repository import get_mission
from orchestrator.task_graph import TaskNode, get_available_tasks, get_task_summary

logger = logging.getLogger(__name__)


async def _fetch_agents_detail(
    redis: Redis,
    pool_size: int,
) -> list[dict[str, str]]:
    """Fetch full state for every agent in the pool."""
    results = []
    for aid in agent_ids(pool_size):
        state = await get_agent_state(redis, aid)
        state["id"] = aid
        results.append(state)
    return results


def _evidence_by_theme(evidence: list[dict[str, Any]]) -> dict[str, int]:
    """Count evidence items grouped by theme."""
    counts: dict[str, int] = {}
    for item in evidence:
        theme = item.get("theme") or "unclassified"
        counts[theme] = counts.get(theme, 0) + 1
    return counts


def _elapsed_seconds(created_at: Any) -> float:
    """Compute seconds elapsed since mission creation."""
    if created_at is None:
        return 0.0
    if isinstance(created_at, datetime):
        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return max(0.0, (now - created_at).total_seconds())
    # Fallback: treat as unix timestamp
    try:
        return max(0.0, time.time() - float(created_at))
    except (TypeError, ValueError):
        return 0.0


async def build_context_packet(
    mission_id: str,
    db: asyncpg.Pool,
    redis: Redis,
    pool_size: int = 6,
) -> dict[str, Any]:
    """Build the full context packet for the orchestrator planning loop.

    Fetches mission, evidence, and pool state concurrently, then derives
    task graph analysis and contradiction count.

    Args:
        mission_id: UUID of the mission.
        db: asyncpg connection pool.
        redis: Redis client.
        pool_size: Number of agents in the pool.

    Returns:
        A flat dict suitable for JSON serialization and LLM consumption.
        Returns a dict with ``mission_id`` and ``error`` key if the
        mission is not found.
    """
    # Fetch mission, evidence, and pool state in parallel
    mission_result, evidence_result, pool_summary, agents_detail = await asyncio.gather(
        get_mission(db, mission_id),
        list_evidence(db, mission_id, limit=50),
        get_pool_summary(redis, pool_size),
        _fetch_agents_detail(redis, pool_size),
        return_exceptions=True,
    )

    # Handle fetch errors gracefully
    mission = mission_result if not isinstance(mission_result, BaseException) else None
    evidence = evidence_result if not isinstance(evidence_result, BaseException) else []
    pool = pool_summary if not isinstance(pool_summary, BaseException) else {}
    agents = agents_detail if not isinstance(agents_detail, BaseException) else []

    if mission is None:
        logger.warning("Mission %s not found during context build", mission_id)
        return {"mission_id": mission_id, "error": "mission_not_found"}

    # Parse task graph
    raw_graph = mission.get("task_graph") or []
    if isinstance(raw_graph, list):
        task_nodes = [TaskNode.from_dict(t) for t in raw_graph]
    else:
        task_nodes = []

    available = get_available_tasks(task_nodes)
    task_summary = get_task_summary(task_nodes)

    elapsed = _elapsed_seconds(mission.get("created_at"))

    # Contradiction count — fetch from Redis cache if available
    contradiction_count = 0
    try:
        import json as _json

        cached = await redis.get(f"mission:{mission_id}:contradictions")
        if cached is not None:
            contradiction_count = len(_json.loads(cached))
    except Exception:
        pass

    # Build the packet
    packet: dict[str, Any] = {
        "mission_id": mission_id,
        "objective": mission.get("objective", ""),
        "status": mission.get("status", "UNKNOWN"),
        "elapsed_sec": round(elapsed, 1),
        "task_summary": task_summary,
        "total_tasks": len(task_nodes),
        "available_tasks": [
            {
                "id": t.id,
                "description": t.description,
                "agent_type": t.agent_type,
                "priority": t.priority,
            }
            for t in available
        ],
        "evidence_count": len(evidence),
        "evidence_by_theme": _evidence_by_theme(evidence),
        "contradiction_count": contradiction_count,
        "agent_pool": pool,
        "agents": [
            {
                "id": a.get("id", ""),
                "status": a.get("status", "IDLE"),
                "task_id": a.get("task_id", ""),
                "agent_type": a.get("agent_type", ""),
            }
            for a in agents
        ],
        "open_questions": [],  # Placeholder for future open-question tracking
    }

    logger.debug(
        "Context packet for %s: %d tasks (%d available), %d evidence, %.0fs elapsed",
        mission_id[:8],
        len(task_nodes),
        len(available),
        len(evidence),
        elapsed,
    )

    return packet
