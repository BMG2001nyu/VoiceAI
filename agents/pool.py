"""Agent pool — fixed pool of 6 named browser agents with Redis state tracking.

Agent state is stored in Redis hashes:
    agent:{id} -> {status, task_id, mission_id, agent_type, session_id, last_heartbeat}

Status values: IDLE, ASSIGNED, BROWSING, REPORTING
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Agent statuses
IDLE = "IDLE"
ASSIGNED = "ASSIGNED"
BROWSING = "BROWSING"
REPORTING = "REPORTING"

VALID_STATUSES = {IDLE, ASSIGNED, BROWSING, REPORTING}


def agent_key(agent_id: str) -> str:
    """Redis hash key for an agent's state."""
    return f"agent:{agent_id}"


def agent_ids(pool_size: int = 6) -> list[str]:
    """Return list of agent IDs for the pool."""
    return [f"agent_{i}" for i in range(pool_size)]


async def init_pool(redis: Any, pool_size: int = 6) -> None:
    """Initialize all agents to IDLE state in Redis.

    Safe to call multiple times -- resets all agents.

    Args:
        redis: aioredis client instance.
        pool_size: Number of agents in the pool (default 6).
    """
    pipe = redis.pipeline()
    for aid in agent_ids(pool_size):
        pipe.hset(
            agent_key(aid),
            mapping={
                "status": IDLE,
                "task_id": "",
                "mission_id": "",
                "agent_type": "",
                "session_id": "",
                "last_heartbeat": str(time.time()),
            },
        )
    await pipe.execute()
    logger.info("Agent pool initialized: %d agents set to IDLE", pool_size)


async def get_agent_state(redis: Any, aid: str) -> dict[str, str]:
    """Get the full state dict for an agent."""
    state = await redis.hgetall(agent_key(aid))
    # Redis returns bytes by default; decode if needed
    return {
        (k.decode() if isinstance(k, bytes) else k): (
            v.decode() if isinstance(v, bytes) else v
        )
        for k, v in state.items()
    }


async def get_idle_agents(redis: Any, pool_size: int = 6) -> list[str]:
    """Return list of agent IDs currently in IDLE state.

    Args:
        redis: aioredis client.
        pool_size: Number of agents to scan.

    Returns:
        List of idle agent IDs (may be empty).
    """
    idle = []
    for aid in agent_ids(pool_size):
        status = await redis.hget(agent_key(aid), "status")
        if status is not None:
            status = status.decode() if isinstance(status, bytes) else status
        if status == IDLE:
            idle.append(aid)
    return idle


async def claim_agent(
    redis: Any,
    aid: str,
    task_id: str,
    mission_id: str,
    agent_type: str = "",
) -> bool:
    """Atomically claim an agent for a task.

    Uses Redis WATCH to prevent race conditions on concurrent claims.

    Args:
        redis: aioredis client.
        aid: Agent ID to claim.
        task_id: Task UUID being assigned.
        mission_id: Mission UUID the task belongs to.
        agent_type: Agent type (e.g., OFFICIAL_SITE).

    Returns:
        True if claimed successfully, False if agent was not IDLE.
    """
    key = agent_key(aid)

    # Check current status
    status = await redis.hget(key, "status")
    if status is not None:
        status = status.decode() if isinstance(status, bytes) else status

    if status != IDLE:
        logger.warning("Cannot claim %s -- status is %s, not IDLE", aid, status)
        return False

    await redis.hset(
        key,
        mapping={
            "status": ASSIGNED,
            "task_id": str(task_id),
            "mission_id": str(mission_id),
            "agent_type": agent_type,
            "last_heartbeat": str(time.time()),
        },
    )
    logger.info("Claimed %s for task %s (mission %s)", aid, task_id, mission_id)
    return True


async def update_agent_status(
    redis: Any,
    aid: str,
    status: str,
    **extra: str,
) -> None:
    """Update an agent's status and optional extra fields.

    Args:
        redis: aioredis client.
        aid: Agent ID.
        status: New status (must be in VALID_STATUSES).
        **extra: Additional fields to set (e.g., session_id="...").
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status {status!r}; must be one of {VALID_STATUSES}")

    mapping = {"status": status, "last_heartbeat": str(time.time()), **extra}
    await redis.hset(agent_key(aid), mapping=mapping)
    logger.debug("Agent %s -> %s", aid, status)


async def release_agent(redis: Any, aid: str) -> None:
    """Release an agent back to IDLE state.

    Clears task_id, mission_id, agent_type, and session_id.

    Args:
        redis: aioredis client.
        aid: Agent ID to release.
    """
    await redis.hset(
        agent_key(aid),
        mapping={
            "status": IDLE,
            "task_id": "",
            "mission_id": "",
            "agent_type": "",
            "session_id": "",
            "last_heartbeat": str(time.time()),
        },
    )
    logger.info("Released %s -> IDLE", aid)


async def get_pool_summary(redis: Any, pool_size: int = 6) -> dict[str, int]:
    """Return a summary count of agents by status.

    Returns:
        Dict like {"IDLE": 4, "ASSIGNED": 1, "BROWSING": 1, "REPORTING": 0}
    """
    counts: dict[str, int] = {s: 0 for s in VALID_STATUSES}
    for aid in agent_ids(pool_size):
        status = await redis.hget(agent_key(aid), "status")
        if status is not None:
            status = status.decode() if isinstance(status, bytes) else status
            if status in counts:
                counts[status] += 1
    return counts
