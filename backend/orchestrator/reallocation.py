"""Agent reallocation triggers — Task 10.4.

Detects conditions under which the orchestrator should redirect
a running agent to a different objective.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import asyncpg
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Thresholds
LOW_YIELD_TIMEOUT_SEC = 20  # Agent browsing with no evidence
COVERAGE_GAP_THRESHOLD = 2  # Min evidence per theme
COVERAGE_CHECK_DELAY_SEC = 15  # Wait before checking gaps


@dataclass
class RedirectAction:
    """A directive to redirect an agent to a new objective."""

    agent_id: str
    new_objective: str
    reason: str


async def detect_reallocation_opportunities(
    mission_id: str,
    agents: list[dict[str, Any]],
    db: asyncpg.Pool,
    redis: Redis | None = None,
    elapsed_sec: float = 0.0,
) -> list[RedirectAction]:
    """Detect agents that should be redirected.

    Triggers:
        1. Low-yield agent: BROWSING > 20s with no evidence.
        2. Contradiction priority: unresolved contradictions with idle agents.
        3. Coverage gap: theme has < 2 evidence items after 15s.

    Args:
        mission_id: UUID of the mission.
        agents: List of agent state dicts (id, status, task_id, last_evidence_at).
        db: asyncpg pool.
        redis: Redis client (optional).
        elapsed_sec: Seconds since mission started.

    Returns:
        List of RedirectAction recommendations.
    """
    actions: list[RedirectAction] = []

    # Trigger 1: Low-yield agents
    now = time.time()
    for agent in agents:
        if agent.get("status") != "BROWSING":
            continue
        last_evidence = agent.get("last_evidence_at", 0)
        if now - last_evidence > LOW_YIELD_TIMEOUT_SEC:
            # Find next pending task
            pending = await db.fetch(
                """
                SELECT id, description FROM tasks
                WHERE mission_id = $1 AND status = 'PENDING'
                ORDER BY priority DESC
                LIMIT 1
                """,
                mission_id,
            )
            if pending:
                actions.append(
                    RedirectAction(
                        agent_id=agent["id"],
                        new_objective=pending[0]["description"],
                        reason=f"Low yield: no evidence for {int(now - last_evidence)}s",
                    )
                )

    # Trigger 2: Contradiction priority
    if redis is not None and elapsed_sec > 10:
        try:
            from evidence.contradictions import detect_contradictions

            contras = await detect_contradictions(mission_id, db, redis)
            if contras:
                idle_agents = [a for a in agents if a.get("status") == "IDLE"]
                if idle_agents:
                    contra = contras[0]
                    actions.append(
                        RedirectAction(
                            agent_id=idle_agents[0]["id"],
                            new_objective=(
                                f"Investigate contradiction: {contra.description}"
                            ),
                            reason="Unresolved contradiction needs investigation",
                        )
                    )
        except Exception as exc:
            logger.debug("Contradiction check failed: %s", exc)

    # Trigger 3: Coverage gaps
    if elapsed_sec > COVERAGE_CHECK_DELAY_SEC:
        try:
            themes = await db.fetch(
                """
                SELECT theme, COUNT(*) as cnt
                FROM evidence
                WHERE mission_id = $1 AND theme IS NOT NULL
                GROUP BY theme
                HAVING COUNT(*) < $2
                """,
                mission_id,
                COVERAGE_GAP_THRESHOLD,
            )
            idle_agents = [
                a
                for a in agents
                if a.get("status") == "IDLE"
                and a["id"] not in {act.agent_id for act in actions}
            ]
            for theme_row, agent in zip(themes, idle_agents):
                actions.append(
                    RedirectAction(
                        agent_id=agent["id"],
                        new_objective=f"Find more evidence about: {theme_row['theme']}",
                        reason=f"Coverage gap: '{theme_row['theme']}' has only {theme_row['cnt']} items",
                    )
                )
        except Exception as exc:
            logger.debug("Coverage gap check failed: %s", exc)

    if actions:
        logger.info(
            "Detected %d reallocation opportunities for mission %s",
            len(actions),
            mission_id,
        )

    return actions
