"""Asyncpg repository functions for the evidence table."""

from __future__ import annotations

import logging
from typing import Any, Optional

import asyncpg

logger = logging.getLogger(__name__)


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    d = dict(row)
    d["id"] = str(d["id"])
    d["mission_id"] = str(d["mission_id"])
    return d


async def insert_evidence(
    pool: asyncpg.Pool,
    mission_id: str,
    agent_id: str,
    claim: str,
    summary: str,
    source_url: str,
    snippet: str,
    confidence: float = 0.8,
    novelty: float = 1.0,
    theme: Optional[str] = None,
    screenshot_s3_key: Optional[str] = None,
) -> dict[str, Any]:
    """Insert a new evidence row and return it."""
    row = await pool.fetchrow(
        """
        INSERT INTO evidence
            (mission_id, agent_id, claim, summary, source_url, snippet,
             confidence, novelty, theme, screenshot_s3_key)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id, mission_id, agent_id, claim, summary, source_url, snippet,
                  confidence, novelty, theme, screenshot_s3_key, timestamp
        """,
        mission_id,
        agent_id,
        claim,
        summary,
        source_url,
        snippet,
        confidence,
        novelty,
        theme,
        screenshot_s3_key,
    )
    return _row_to_dict(row)


async def list_evidence(
    pool: asyncpg.Pool,
    mission_id: str,
    theme: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List evidence for a mission with optional theme filter and pagination."""
    if theme is not None:
        rows = await pool.fetch(
            """
            SELECT id, mission_id, agent_id, claim, summary, source_url, snippet,
                   confidence, novelty, theme, screenshot_s3_key, timestamp
            FROM evidence
            WHERE mission_id = $1 AND theme = $2
            ORDER BY timestamp DESC
            LIMIT $3 OFFSET $4
            """,
            mission_id,
            theme,
            limit,
            offset,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT id, mission_id, agent_id, claim, summary, source_url, snippet,
                   confidence, novelty, theme, screenshot_s3_key, timestamp
            FROM evidence
            WHERE mission_id = $1
            ORDER BY timestamp DESC
            LIMIT $2 OFFSET $3
            """,
            mission_id,
            limit,
            offset,
        )
    return [_row_to_dict(r) for r in rows]
