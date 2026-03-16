"""FastAPI router — Mission CRUD endpoints."""

from __future__ import annotations

import asyncio
import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis

from deps import get_db, get_redis
from missions.schemas import MissionCreate, MissionResponse, MissionUpdate
from missions import repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/missions", tags=["missions"])

# In-memory registry of running planning-loop tasks, keyed by mission_id.
# Used to cancel a loop when the mission is stopped or completed.
_planning_tasks: dict[str, asyncio.Task] = {}


async def _publish_status_change(redis: Redis, mission: dict) -> None:
    """Publish a STATUS_CHANGE event so the WS relay forwards it to the browser."""
    # Import here to avoid a circular dependency before streaming/ exists.
    try:
        from streaming.channels import publish

        await publish(redis, mission["id"], "MISSION_STATUS", mission)
    except Exception:
        logger.warning("Could not publish STATUS_CHANGE; streaming not wired yet")


@router.post("", response_model=MissionResponse, status_code=201)
async def create_mission(
    body: MissionCreate,
    db: asyncpg.Pool = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MissionResponse:
    """Create a mission, decompose it into tasks via Nova Lite, return the mission."""
    from config import settings

    mission = await repository.create_mission(db, body.objective)
    mission_id = mission["id"]

    if settings.demo_mode:
        task_graph = _demo_task_graph(body.objective)
    else:
        try:
            from models.lite_client import LiteClient

            client = LiteClient(api_key=settings.nova_api_key)
            task_graph = await client.plan_tasks(body.objective)
        except Exception as exc:
            logger.error("plan_tasks failed for mission %s: %s", mission_id, exc)
            task_graph = _demo_task_graph(body.objective)

    mission = await repository.set_task_graph(db, mission_id, task_graph)
    await _publish_status_change(redis, mission)

    # Start the orchestrator planning loop as a background task if mission is ACTIVE.
    if mission.get("status") == "ACTIVE":
        _start_loop(mission_id, db, redis)

    return MissionResponse(**mission)


@router.get("/{mission_id}", response_model=MissionResponse)
async def get_mission(
    mission_id: str,
    db: asyncpg.Pool = Depends(get_db),
) -> MissionResponse:
    mission = await repository.get_mission(db, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return MissionResponse(**mission)


@router.patch("/{mission_id}", response_model=MissionResponse)
async def update_mission(
    mission_id: str,
    body: MissionUpdate,
    db: asyncpg.Pool = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MissionResponse:
    # Valid forward transitions — terminal states (COMPLETE, FAILED) are immutable.
    _VALID_TRANSITIONS: dict[str, set[str]] = {
        "PENDING": {"ACTIVE", "FAILED"},
        "ACTIVE": {"SYNTHESIZING", "FAILED"},
        "SYNTHESIZING": {"COMPLETE", "FAILED"},
        "COMPLETE": set(),
        "FAILED": set(),
    }
    valid_statuses = set(_VALID_TRANSITIONS.keys())
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    current = await repository.get_mission(db, mission_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Mission not found")

    allowed = _VALID_TRANSITIONS.get(current["status"], set())
    if body.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot transition from {current['status']} to {body.status}. "
                f"Allowed next states: {sorted(allowed) or ['none (terminal)']}"
            ),
        )

    mission = await repository.update_mission_status(db, mission_id, body.status)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Cancel the planning loop if the mission moved to a terminal state.
    if body.status in {"SYNTHESIZING", "COMPLETE", "FAILED"}:
        _cancel_loop(mission_id)

    await _publish_status_change(redis, mission)
    return MissionResponse(**mission)


# ── Synthesize endpoint ──────────────────────────────────────────────────────


@router.post("/{mission_id}/synthesize", response_model=MissionResponse)
async def synthesize_mission(
    mission_id: str,
    db: asyncpg.Pool = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MissionResponse:
    """Manually trigger synthesis for a mission (the SYNTHESIZE INTELLIGENCE button)."""
    current = await repository.get_mission(db, mission_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Mission not found")

    if current["status"] not in ("ACTIVE", "SYNTHESIZING"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot synthesize from status {current['status']}",
        )

    # Cancel planning loop if still running.
    _cancel_loop(mission_id)

    # Transition to SYNTHESIZING (if not already there).
    if current["status"] != "SYNTHESIZING":
        await repository.update_mission_status(db, mission_id, "SYNTHESIZING")
        mission_after = await repository.get_mission(db, mission_id)
        if mission_after is not None:
            await _publish_status_change(redis, mission_after)

    # Run synthesis pipeline.
    briefing_text = await _run_synthesis(mission_id, db, redis)

    # Store briefing and mark COMPLETE.
    completed = await repository.set_briefing(db, mission_id, briefing_text)
    if completed is None:
        raise HTTPException(status_code=500, detail="Failed to store briefing")

    await _publish_status_change(redis, completed)
    return MissionResponse(**completed)


# ── Internal helpers ─────────────────────────────────────────────────────────


def _start_loop(mission_id: str, db: asyncpg.Pool, redis: Redis) -> None:
    """Start the planning loop for *mission_id* and track the task."""
    from orchestrator.planning_loop import start_planning_loop

    # Don't start a second loop for the same mission.
    existing = _planning_tasks.get(mission_id)
    if existing is not None and not existing.done():
        logger.debug("Planning loop already running for %s", mission_id)
        return

    task = start_planning_loop(mission_id, db, redis)

    def _on_done(t: asyncio.Task) -> None:
        _planning_tasks.pop(mission_id, None)

    task.add_done_callback(_on_done)
    _planning_tasks[mission_id] = task
    logger.info("Planning loop started for mission %s", mission_id)


def _cancel_loop(mission_id: str) -> None:
    """Cancel the planning-loop task for *mission_id* if running."""
    task = _planning_tasks.pop(mission_id, None)
    if task is not None and not task.done():
        task.cancel()
        logger.info("Cancelled planning loop for mission %s", mission_id)


async def _run_synthesis(mission_id: str, db: asyncpg.Pool, redis: Redis) -> str:
    """Run the synthesis pipeline, falling back to a simple briefing on error."""
    from config import settings

    if settings.demo_mode:
        return await _demo_synthesis(mission_id, db, redis)

    try:
        from synthesis.spoken_briefing import run_synthesis_pipeline

        return await run_synthesis_pipeline(mission_id, db, redis)
    except Exception as exc:
        logger.error("Synthesis pipeline failed for %s: %s", mission_id, exc)
        return _fallback_briefing(mission_id)


async def _demo_synthesis(mission_id: str, db: asyncpg.Pool, redis: Redis) -> str:
    """Generate a demo-mode briefing from evidence already in the DB."""
    from evidence.repository import list_evidence

    rows = await list_evidence(db, mission_id, limit=50)
    mission = await repository.get_mission(db, mission_id)
    objective = mission["objective"] if mission else "Unknown objective"

    # Group evidence by theme.
    themes: dict[str, list[str]] = {}
    for row in rows:
        theme = row.get("theme") or "General"
        themes.setdefault(theme, []).append(row.get("claim", ""))

    lines = [
        "# Intelligence Briefing\n",
        f"**Objective:** {objective}\n",
        "## Executive Summary\n",
        f"Our research team gathered {len(rows)} evidence items across "
        f"{len(themes)} themes.\n",
        "## Key Findings\n",
    ]
    for theme, claims in themes.items():
        lines.append(f"### {theme}")
        for claim in claims[:3]:
            lines.append(f"- {claim}")
        lines.append("")

    lines.append("## Recommendations\n")
    lines.append("- Validate high-confidence claims with primary sources")
    lines.append("- Investigate themes with low evidence coverage")

    briefing = "\n".join(lines)

    # Publish timeline event for synthesis completion.
    try:
        import uuid as _uuid
        from datetime import datetime, timezone
        from streaming.channels import publish_timeline_event

        await publish_timeline_event(
            redis,
            mission_id,
            {
                "id": str(_uuid.uuid4()),
                "type": "synthesis_complete",
                "description": "Intelligence briefing generated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"briefing_length": len(briefing)},
            },
        )
    except Exception as exc:
        logger.warning("Could not publish synthesis timeline event: %s", exc)

    return briefing


def _demo_task_graph(objective: str) -> list[dict]:
    """Generate a hardcoded task graph for demo mode (no LLM call)."""
    return [
        {
            "description": f"Search official company websites for {objective}",
            "agent_type": "OFFICIAL_SITE",
            "priority": 9,
            "dependencies": [],
        },
        {
            "description": f"Find recent news and blog posts about {objective}",
            "agent_type": "NEWS_BLOG",
            "priority": 8,
            "dependencies": [],
        },
        {
            "description": f"Scan Reddit and Hacker News for sentiment on {objective}",
            "agent_type": "REDDIT_HN",
            "priority": 7,
            "dependencies": [],
        },
        {
            "description": f"Analyze GitHub repos and technical footprint for {objective}",
            "agent_type": "GITHUB",
            "priority": 6,
            "dependencies": [],
        },
        {
            "description": f"Research financial data and funding history for {objective}",
            "agent_type": "FINANCIAL",
            "priority": 7,
            "dependencies": [],
        },
        {
            "description": f"Find breaking news from last 6 months about {objective}",
            "agent_type": "RECENT_NEWS",
            "priority": 8,
            "dependencies": [],
        },
    ]


def _fallback_briefing(mission_id: str) -> str:
    """Minimal briefing when synthesis completely fails."""
    return (
        "# Intelligence Briefing\n\n"
        "Synthesis was unable to process the evidence for this mission. "
        "Please review the evidence board manually.\n\n"
        f"Mission ID: {mission_id}"
    )
