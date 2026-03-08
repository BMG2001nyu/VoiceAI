"""Asyncpg repository functions for the missions table."""

from __future__ import annotations

import json
import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    """Convert an asyncpg Record to a plain dict, normalising types."""
    d = dict(row)
    d["id"] = str(d["id"])
    # JSONB columns are returned as strings by asyncpg; parse them to Python objects.
    tg = d.get("task_graph")
    if isinstance(tg, str):
        d["task_graph"] = json.loads(tg)
    return d


async def create_mission(pool: asyncpg.Pool, objective: str) -> dict[str, Any]:
    """Insert a new mission row with status PENDING and return it."""
    row = await pool.fetchrow(
        """
        INSERT INTO missions (objective, status)
        VALUES ($1, 'PENDING')
        RETURNING id, objective, status, task_graph, created_at, updated_at, briefing
        """,
        objective,
    )
    return _row_to_dict(row)


async def set_task_graph(
    pool: asyncpg.Pool,
    mission_id: str,
    task_graph: list[dict[str, Any]],
    status: str = "ACTIVE",
) -> dict[str, Any]:
    """Store the task graph and advance the mission to ACTIVE (or given status)."""
    row = await pool.fetchrow(
        """
        UPDATE missions
        SET task_graph = $2::jsonb,
            status     = $3::mission_status,
            updated_at = NOW()
        WHERE id = $1
        RETURNING id, objective, status, task_graph, created_at, updated_at, briefing
        """,
        mission_id,
        json.dumps(task_graph),
        status,
    )
    return _row_to_dict(row)


async def get_mission(pool: asyncpg.Pool, mission_id: str) -> dict[str, Any] | None:
    """Fetch a single mission by ID; returns None if not found."""
    row = await pool.fetchrow(
        """
        SELECT id, objective, status, task_graph, created_at, updated_at, briefing
        FROM missions
        WHERE id = $1
        """,
        mission_id,
    )
    if row is None:
        return None
    return _row_to_dict(row)


async def update_mission_status(
    pool: asyncpg.Pool, mission_id: str, status: str
) -> dict[str, Any] | None:
    """Update mission status and return the updated row; None if not found."""
    row = await pool.fetchrow(
        """
        UPDATE missions
        SET status     = $2::mission_status,
            updated_at = NOW()
        WHERE id = $1
        RETURNING id, objective, status, task_graph, created_at, updated_at, briefing
        """,
        mission_id,
        status,
    )
    if row is None:
        return None
    return _row_to_dict(row)


async def set_briefing(
    pool: asyncpg.Pool, mission_id: str, briefing: str
) -> dict[str, Any] | None:
    """Store the final briefing text and mark the mission COMPLETE."""
    row = await pool.fetchrow(
        """
        UPDATE missions
        SET briefing   = $2,
            status     = 'COMPLETE'::mission_status,
            updated_at = NOW()
        WHERE id = $1
        RETURNING id, objective, status, task_graph, created_at, updated_at, briefing
        """,
        mission_id,
        briefing,
    )
    if row is None:
        return None
    return _row_to_dict(row)
