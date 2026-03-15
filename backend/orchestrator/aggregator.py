"""Agent result aggregation — Task 11.4.

Handles agent task completion signals, updates state, and
triggers the next planning cycle.
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

TASK_EVIDENCE_THRESHOLD = 3  # Evidence count that marks a task as done
TASK_TIMEOUT_SEC = 60  # Max time before force-completing a task


async def handle_task_completion(
    agent_id: str,
    task_id: str,
    mission_id: str,
    db: asyncpg.Pool,
    redis: Redis | None = None,
) -> None:
    """Process an agent's task completion.

    Steps:
        1. Set task status to DONE in Postgres.
        2. Set agent status to IDLE in Redis.
        3. Publish TIMELINE_EVENT.
        4. Signal next planning cycle.

    Args:
        agent_id: ID of the completing agent.
        task_id: ID of the completed task.
        mission_id: UUID of the mission.
        db: asyncpg pool.
        redis: Redis client.
    """
    # Step 1: Mark task DONE
    await db.execute(
        "UPDATE tasks SET status = 'DONE' WHERE id = $1",
        task_id,
    )
    logger.info("Task %s marked DONE (agent %s)", task_id, agent_id)

    # Step 2: Set agent to IDLE in Redis
    if redis is not None:
        try:
            await redis.hset(
                f"agent:{agent_id}",
                mapping={"status": "IDLE", "task_id": ""},
            )
        except Exception as exc:
            logger.warning("Could not update agent state in Redis: %s", exc)

    # Step 3: Publish timeline event
    if redis is not None:
        try:
            from streaming.channels import publish

            await publish(
                redis,
                mission_id,
                "TIMELINE_EVENT",
                {
                    "type": "agent_completed",
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "message": f"Agent {agent_id} completed task",
                },
            )
        except Exception as exc:
            logger.warning("Could not publish completion event: %s", exc)

    # Step 4: Signal immediate planning cycle
    if redis is not None:
        try:
            await redis.publish(
                f"mission:{mission_id}:planning_trigger",
                "task_completed",
            )
        except Exception as exc:
            logger.debug("Could not signal planning cycle: %s", exc)


async def check_evidence_threshold(
    agent_id: str,
    task_id: str,
    mission_id: str,
    db: asyncpg.Pool,
    redis: Redis | None = None,
) -> bool:
    """Check if evidence count for an agent's task exceeds the threshold.

    If so, trigger task completion.

    Returns:
        True if threshold was met and completion was triggered.
    """
    count = await db.fetchval(
        """
        SELECT COUNT(*) FROM evidence
        WHERE mission_id = $1 AND agent_id = $2
        """,
        mission_id,
        agent_id,
    )

    if count is not None and count >= TASK_EVIDENCE_THRESHOLD:
        await handle_task_completion(
            agent_id=agent_id,
            task_id=task_id,
            mission_id=mission_id,
            db=db,
            redis=redis,
        )
        return True

    return False


async def force_complete_timed_out_agents(
    mission_id: str,
    agents: list[dict[str, Any]],
    db: asyncpg.Pool,
    redis: Redis | None = None,
    elapsed_sec: float = 0.0,
) -> list[str]:
    """Force-complete agents that have exceeded the timeout.

    Prevents stuck agents from blocking synthesis.

    Returns:
        List of agent IDs that were force-completed.
    """
    import time

    force_completed = []
    now = time.time()

    for agent in agents:
        if agent.get("status") not in ("BROWSING", "ASSIGNED"):
            continue

        assigned_at = agent.get("assigned_at", now)
        if now - assigned_at > TASK_TIMEOUT_SEC:
            task_id = agent.get("task_id", "")
            if task_id:
                await handle_task_completion(
                    agent_id=agent["id"],
                    task_id=task_id,
                    mission_id=mission_id,
                    db=db,
                    redis=redis,
                )
                force_completed.append(agent["id"])
                logger.warning(
                    "Force-completed agent %s (task %s) after %ds timeout",
                    agent["id"],
                    task_id,
                    TASK_TIMEOUT_SEC,
                )

    return force_completed
