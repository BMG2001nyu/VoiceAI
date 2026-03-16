"""Orchestrator planning loop — the main decision engine for Mission Control.

Runs as an asyncio background task, cycling every PLANNING_CYCLE_INTERVAL_SEC
until the mission reaches a terminal state. Each cycle builds a context packet,
checks stopping/reallocation criteria, assigns tasks, and dispatches commands.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

import asyncpg
from redis.asyncio import Redis

from agents.command_channel import dispatch_commands
from config import settings
from missions.repository import get_mission, update_mission_status
from orchestrator.assignment import assign_tasks
from orchestrator.context_packet import build_context_packet
from orchestrator.reallocation import detect_reallocation_opportunities
from orchestrator.stopping import should_stop
from orchestrator.task_graph import TaskNode, get_available_tasks
from streaming.channels import publish_timeline_event

logger = logging.getLogger(__name__)

# How often the planning loop runs (seconds)
PLANNING_CYCLE_INTERVAL_SEC = 10

# Terminal statuses — the loop stops when the mission enters one of these
_TERMINAL_STATUSES = {"SYNTHESIZING", "COMPLETE", "FAILED", "CANCELLED"}


async def run_planning_loop(
    mission_id: str,
    db: asyncpg.Pool,
    redis: Redis,
) -> None:
    """Main orchestrator loop — runs until the mission completes or is stopped.

    Each cycle:
        1. Fetch mission and verify it is still ACTIVE.
        2. Build context packet.
        3. Check stopping criteria; if met, transition to SYNTHESIZING.
        4. Check reallocation triggers and redirect agents.
        5. Get available tasks + idle agents and assign via assign_tasks().
        6. Dispatch BROWSE commands to agents.
        7. Publish TIMELINE_EVENT for actions taken.
        8. Sleep for PLANNING_CYCLE_INTERVAL_SEC, then repeat.

    Args:
        mission_id: UUID of the mission to orchestrate.
        db: asyncpg connection pool.
        redis: Redis client.
    """
    pool_size = settings.agent_pool_size
    cycle = 0

    logger.info("Planning loop started for mission %s", mission_id)

    try:
        while True:
            cycle += 1
            actions_taken: list[str] = []

            try:
                # ── 1. Verify mission exists and is ACTIVE ──────────────
                mission = await get_mission(db, mission_id)
                if mission is None:
                    logger.warning(
                        "Mission %s not found — stopping planning loop", mission_id
                    )
                    break

                status = mission.get("status", "")
                if status in _TERMINAL_STATUSES:
                    logger.info(
                        "Mission %s is %s — stopping planning loop",
                        mission_id,
                        status,
                    )
                    break

                if status != "ACTIVE":
                    logger.debug(
                        "Mission %s status is %s (not ACTIVE) — skipping cycle %d",
                        mission_id,
                        status,
                        cycle,
                    )
                    await asyncio.sleep(PLANNING_CYCLE_INTERVAL_SEC)
                    continue

                # ── 2. Build context packet ─────────────────────────────
                context = await build_context_packet(mission_id, db, redis, pool_size)

                if context.get("error"):
                    logger.warning(
                        "Context build error for %s: %s",
                        mission_id,
                        context.get("error"),
                    )
                    break

                elapsed_sec = context.get("elapsed_sec", 0.0)

                # ── 3. Check stopping criteria ──────────────────────────
                stop, reason = await should_stop(mission_id, elapsed_sec, db)

                if stop:
                    logger.info(
                        "Stopping mission %s (cycle %d): %s",
                        mission_id,
                        cycle,
                        reason,
                    )
                    await update_mission_status(db, mission_id, "SYNTHESIZING")
                    await _publish_stop_event(redis, mission_id, reason)
                    actions_taken.append(f"STOP: {reason}")

                    # Trigger synthesis pipeline.
                    await _trigger_synthesis(mission_id, db, redis)
                    break

                # ── 4. Check reallocation triggers ──────────────────────
                agents_state = context.get("agents", [])
                redirects = await detect_reallocation_opportunities(
                    mission_id,
                    agents_state,
                    db,
                    redis=redis,
                    elapsed_sec=elapsed_sec,
                )

                for redirect in redirects:
                    await _publish_redirect_event(
                        redis, mission_id, redirect.agent_id, redirect.reason
                    )
                    actions_taken.append(
                        f"REDIRECT {redirect.agent_id}: {redirect.reason}"
                    )

                # ── 5. Assign available tasks to idle agents ────────────
                raw_graph = mission.get("task_graph") or []
                task_nodes = (
                    [TaskNode.from_dict(t) for t in raw_graph]
                    if isinstance(raw_graph, list)
                    else []
                )
                available = get_available_tasks(task_nodes)

                assignments = await assign_tasks(available, redis, pool_size)

                # ── 6. Dispatch commands ────────────────────────────────
                if assignments:
                    dispatched = await dispatch_commands(assignments, redis, mission_id)
                    actions_taken.append(f"ASSIGNED {dispatched} agents")

                    # ── 6b. In demo mode, spawn simulated agents ──────
                    if settings.demo_mode:
                        try:
                            from demo.demo_runner import run_demo_agents_batch

                            await run_demo_agents_batch(
                                assignments, mission_id, db, redis
                            )
                        except Exception as exc:
                            logger.error(
                                "Demo runner failed for mission %s: %s",
                                mission_id,
                                exc,
                            )

                    # ── 7. Publish timeline events ──────────────────────
                    for action in assignments:
                        await _publish_assign_event(
                            redis,
                            mission_id,
                            action.agent_id,
                            action.task_id,
                            action.objective,
                        )

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Planning loop error (mission=%s, cycle=%d)",
                    mission_id,
                    cycle,
                )

            # Log cycle summary
            logger.info(
                "Planning cycle %d for %s: %s",
                cycle,
                mission_id[:8],
                "; ".join(actions_taken) if actions_taken else "no actions",
            )

            await asyncio.sleep(PLANNING_CYCLE_INTERVAL_SEC)

    except asyncio.CancelledError:
        logger.info("Planning loop cancelled for mission %s", mission_id)

    logger.info("Planning loop ended for mission %s after %d cycles", mission_id, cycle)


# ── Lifecycle helpers ────────────────────────────────────────────────────────


def start_planning_loop(
    mission_id: str,
    db: asyncpg.Pool,
    redis: Redis,
) -> asyncio.Task:
    """Start the planning loop as a background asyncio task.

    Args:
        mission_id: UUID of the mission to orchestrate.
        db: asyncpg connection pool.
        redis: Redis client.

    Returns:
        The asyncio.Task running the loop (cancel to stop).
    """
    task = asyncio.create_task(
        run_planning_loop(mission_id, db, redis),
        name=f"planning:{mission_id[:8]}",
    )
    logger.info("Started planning loop task for mission %s", mission_id)
    return task


# ── Timeline event publishers ────────────────────────────────────────────────


async def _publish_stop_event(
    redis: Redis,
    mission_id: str,
    reason: str,
) -> None:
    """Publish a timeline event for mission stop."""
    await publish_timeline_event(
        redis,
        mission_id,
        {
            "id": str(uuid.uuid4()),
            "type": "mission_synthesizing",
            "description": f"Mission transitioning to synthesis: {reason}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"reason": reason},
        },
    )


async def _publish_redirect_event(
    redis: Redis,
    mission_id: str,
    agent_id: str,
    reason: str,
) -> None:
    """Publish a timeline event for agent redirection."""
    await publish_timeline_event(
        redis,
        mission_id,
        {
            "id": str(uuid.uuid4()),
            "type": "agent_redirected",
            "description": f"Agent {agent_id} redirected: {reason}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"agent_id": agent_id, "reason": reason},
        },
    )


async def _publish_assign_event(
    redis: Redis,
    mission_id: str,
    agent_id: str,
    task_id: str,
    objective: str,
) -> None:
    """Publish a timeline event for agent assignment."""
    await publish_timeline_event(
        redis,
        mission_id,
        {
            "id": str(uuid.uuid4()),
            "type": "agent_assigned",
            "description": f"Agent {agent_id} assigned: {objective[:80]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "agent_id": agent_id,
                "task_id": task_id,
                "objective": objective,
            },
        },
    )


# ── Synthesis trigger ────────────────────────────────────────────────────────


async def _trigger_synthesis(
    mission_id: str,
    db: asyncpg.Pool,
    redis: Redis,
) -> None:
    """Run the synthesis pipeline after the planning loop stops.

    In demo mode, builds a briefing from DB evidence.
    In production mode, runs the full synthesis pipeline.
    """
    from missions.repository import set_briefing
    from streaming.channels import publish

    logger.info("Starting synthesis for mission %s", mission_id)

    try:
        if settings.demo_mode:
            briefing_text = await _demo_briefing(mission_id, db, redis)
        else:
            from synthesis.spoken_briefing import run_synthesis_pipeline

            briefing_text = await run_synthesis_pipeline(mission_id, db, redis)
    except Exception as exc:
        logger.error("Synthesis failed for %s: %s", mission_id, exc)
        briefing_text = (
            "# Intelligence Briefing\n\n"
            "Synthesis encountered an error. Please review evidence manually.\n\n"
            f"Mission ID: {mission_id}"
        )

    # Store briefing and mark COMPLETE.
    completed = await set_briefing(db, mission_id, briefing_text)

    # Publish final status.
    if completed is not None:
        await publish(redis, mission_id, "MISSION_STATUS", completed)

    # Publish synthesis_complete timeline event.
    await publish_timeline_event(
        redis,
        mission_id,
        {
            "id": str(uuid.uuid4()),
            "type": "synthesis_complete",
            "description": "Intelligence briefing generated — mission complete",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"briefing_length": len(briefing_text)},
        },
    )

    logger.info(
        "Synthesis complete for mission %s (%d chars)", mission_id, len(briefing_text)
    )


async def _demo_briefing(
    mission_id: str,
    db: asyncpg.Pool,
    redis: Redis,
) -> str:
    """Generate a briefing from DB evidence in demo mode (no LLM call)."""
    from evidence.repository import list_evidence
    from missions.repository import get_mission

    rows = await list_evidence(db, mission_id, limit=50)
    mission = await get_mission(db, mission_id)
    objective = mission["objective"] if mission else "Unknown objective"

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

    return "\n".join(lines)
