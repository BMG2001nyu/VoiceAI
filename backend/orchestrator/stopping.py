"""Mission stopping criteria — Task 10.5.

Determines when a mission should transition from ACTIVE to SYNTHESIZING.
"""

from __future__ import annotations

import logging

import asyncpg

logger = logging.getLogger(__name__)

# Thresholds
TIME_BUDGET_SEC = 40  # Stop at 40s (5s buffer before 45s target)
EVIDENCE_PER_TASK_THRESHOLD = 3  # Min evidence per task for coverage


async def should_stop(
    mission_id: str,
    elapsed_sec: float,
    db: asyncpg.Pool,
    lite_vote: str | None = None,
) -> tuple[bool, str]:
    """Check if a mission should stop and transition to SYNTHESIZING.

    Criteria (any one triggers stop):
        1. Time budget exceeded (40s).
        2. All tasks completed (no PENDING/ASSIGNED).
        3. Nova Lite vote ("synthesize").
        4. Coverage threshold met (every task has >= 3 evidence items).

    Args:
        mission_id: UUID of the mission.
        elapsed_sec: Seconds since mission started.
        db: asyncpg pool.
        lite_vote: Action string from Nova Lite planning response.

    Returns:
        Tuple of (should_stop, reason).
    """
    # Criterion 1: Time budget
    if elapsed_sec >= TIME_BUDGET_SEC:
        return True, f"Time budget exceeded ({elapsed_sec:.0f}s >= {TIME_BUDGET_SEC}s)"

    # Criterion 2: Nova Lite vote
    if lite_vote and lite_vote.lower() in ("synthesize", "stop", "complete"):
        return True, f"Nova Lite voted to {lite_vote}"

    # Criterion 3: All tasks done
    pending_count = await db.fetchval(
        """
        SELECT COUNT(*) FROM tasks
        WHERE mission_id = $1 AND status IN ('PENDING', 'ASSIGNED')
        """,
        mission_id,
    )
    if pending_count == 0:
        total = await db.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE mission_id = $1",
            mission_id,
        )
        if total > 0:
            return True, "All tasks completed"

    # Criterion 4: Coverage threshold
    try:
        under_covered = await db.fetchval(
            """
            SELECT COUNT(DISTINCT t.id)
            FROM tasks t
            LEFT JOIN evidence e ON e.mission_id = t.mission_id
                AND e.theme IS NOT NULL
            WHERE t.mission_id = $1
                AND t.status != 'DONE'
            GROUP BY t.id
            HAVING COUNT(e.id) < $2
            """,
            mission_id,
            EVIDENCE_PER_TASK_THRESHOLD,
        )
        # If no under-covered tasks remain, we have sufficient coverage
        if under_covered is None or under_covered == 0:
            evidence_total = await db.fetchval(
                "SELECT COUNT(*) FROM evidence WHERE mission_id = $1",
                mission_id,
            )
            if evidence_total and evidence_total >= EVIDENCE_PER_TASK_THRESHOLD:
                return True, "Coverage threshold met for all tasks"
    except Exception as exc:
        logger.debug("Coverage check query failed: %s", exc)

    return False, ""


async def trigger_synthesis(
    mission_id: str,
    reason: str,
    db: asyncpg.Pool,
) -> None:
    """Transition mission to SYNTHESIZING and trigger the synthesis pipeline.

    Args:
        mission_id: UUID of the mission.
        reason: Why synthesis was triggered.
        db: asyncpg pool.
    """
    from missions.repository import update_mission_status

    logger.info(
        "Triggering synthesis for mission %s: %s",
        mission_id,
        reason,
    )

    await update_mission_status(db, mission_id, "SYNTHESIZING")

    # Kick off synthesis pipeline asynchronously
    try:
        from synthesis.spoken_briefing import run_synthesis_pipeline

        await run_synthesis_pipeline(mission_id, db)
    except Exception as exc:
        logger.error("Synthesis pipeline failed for mission %s: %s", mission_id, exc)
