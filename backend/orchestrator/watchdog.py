"""Heartbeat timeout watchdog — reclaims agents that miss their heartbeat.

Runs as a background asyncio task, scanning all agents every 30 seconds.
If an agent's heartbeat key has expired (TTL elapsed), the watchdog:
1. Resets the agent to IDLE
2. Marks its task as PENDING for reassignment
3. Emits a TIMELINE_EVENT for the War Room UI
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Scan interval
WATCHDOG_INTERVAL_S = 30


async def watchdog(
    redis: Any,
    db: Any,
    pool_size: int = 6,
) -> None:
    """Background task that monitors agent heartbeats and reclaims timed-out agents.

    Runs indefinitely until cancelled.

    Args:
        redis: aioredis client.
        db: asyncpg connection pool.
        pool_size: Number of agents to monitor.
    """
    logger.info(
        "Watchdog started (interval=%ds, pool_size=%d)", WATCHDOG_INTERVAL_S, pool_size
    )

    try:
        while True:
            await asyncio.sleep(WATCHDOG_INTERVAL_S)
            await _scan_agents(redis, db, pool_size)
    except asyncio.CancelledError:
        logger.info("Watchdog stopped")


async def _scan_agents(redis: Any, db: Any, pool_size: int) -> None:
    """Scan all agents and reclaim any with expired heartbeats."""
    for i in range(pool_size):
        agent_id = f"agent_{i}"

        try:
            await _check_agent(redis, db, agent_id)
        except Exception as exc:
            logger.error("Watchdog error checking %s: %s", agent_id, exc)


async def _check_agent(redis: Any, db: Any, agent_id: str) -> None:
    """Check a single agent's heartbeat and reclaim if timed out."""
    from agents.pool import agent_key, release_agent

    key = agent_key(agent_id)
    hb_key = f"agent:{agent_id}:heartbeat"

    # Get agent status
    status_raw = await redis.hget(key, "status")
    if status_raw is None:
        return

    status = status_raw.decode() if isinstance(status_raw, bytes) else status_raw

    # Only check agents that should have heartbeats
    if status not in ("ASSIGNED", "BROWSING"):
        return

    # Check heartbeat
    alive = await redis.get(hb_key)

    if alive is not None:
        return  # Heartbeat is alive — agent is fine

    # Heartbeat expired — reclaim the agent
    logger.warning(
        "Agent %s heartbeat expired (status=%s) — reclaiming", agent_id, status
    )

    # Get task info before resetting
    task_id_raw = await redis.hget(key, "task_id")
    mission_id_raw = await redis.hget(key, "mission_id")

    task_id = (
        (task_id_raw.decode() if isinstance(task_id_raw, bytes) else task_id_raw)
        if task_id_raw
        else None
    )
    mission_id = (
        (
            mission_id_raw.decode()
            if isinstance(mission_id_raw, bytes)
            else mission_id_raw
        )
        if mission_id_raw
        else None
    )

    # Reset agent to IDLE
    await release_agent(redis, agent_id)

    # Reset task to PENDING for reassignment
    if task_id and db:
        try:
            await db.execute(
                "UPDATE tasks SET status = 'PENDING', assigned_agent = NULL WHERE id = $1",
                task_id,
            )
            logger.info("Reset task %s to PENDING", task_id)
        except Exception as exc:
            logger.warning("Failed to reset task %s: %s", task_id, exc)

    # Emit timeline event
    if mission_id:
        try:
            from streaming.channels import publish_timeline_event

            await publish_timeline_event(
                redis,
                mission_id,
                {
                    "id": str(uuid.uuid4()),
                    "type": "agent_timeout",
                    "description": f"Agent {agent_id} timed out and was reclaimed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"agent_id": agent_id, "task_id": task_id},
                },
            )
        except Exception as exc:
            logger.warning("Failed to publish timeout event: %s", exc)


async def start_watchdog(
    redis: Any,
    db: Any,
    pool_size: int = 6,
) -> asyncio.Task:
    """Start the watchdog as a background asyncio task.

    Args:
        redis: aioredis client.
        db: asyncpg connection pool.
        pool_size: Number of agents to monitor.

    Returns:
        The asyncio.Task running the watchdog (cancel to stop).
    """
    task = asyncio.create_task(
        watchdog(redis, db, pool_size),
        name="watchdog",
    )
    return task
