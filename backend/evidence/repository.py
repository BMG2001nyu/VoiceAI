"""Asyncpg repository functions for the evidence table."""

from __future__ import annotations

import logging
from typing import Any, Optional

import asyncpg

logger = logging.getLogger(__name__)

_SELECT_COLS = (
    "id, mission_id, agent_id, claim, summary, source_url, snippet, "
    "confidence, novelty, theme, screenshot_s3_key, embedding_id, timestamp"
)


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
        f"""
        INSERT INTO evidence
            (mission_id, agent_id, claim, summary, source_url, snippet,
             confidence, novelty, theme, screenshot_s3_key)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING {_SELECT_COLS}
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
            f"""
            SELECT {_SELECT_COLS}
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
            f"""
            SELECT {_SELECT_COLS}
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


async def update_screenshot_key(
    pool: asyncpg.Pool,
    evidence_id: str,
    screenshot_s3_key: str,
) -> None:
    """Set the screenshot_s3_key on an evidence record after S3 upload."""
    await pool.execute(
        "UPDATE evidence SET screenshot_s3_key = $1 WHERE id = $2",
        screenshot_s3_key,
        evidence_id,
    )


async def update_confidence(
    pool: asyncpg.Pool,
    evidence_id: str,
    confidence: float,
) -> None:
    """Update the confidence score on an evidence record."""
    await pool.execute(
        "UPDATE evidence SET confidence = $1 WHERE id = $2",
        confidence,
        evidence_id,
    )


async def update_novelty(
    pool: asyncpg.Pool,
    evidence_id: str,
    novelty: float,
) -> None:
    """Update the novelty score on an evidence record."""
    await pool.execute(
        "UPDATE evidence SET novelty = $1 WHERE id = $2",
        novelty,
        evidence_id,
    )


async def update_embedding_id(
    pool: asyncpg.Pool,
    evidence_id: str,
    embedding_id: str,
) -> None:
    """Store the OpenSearch document ID on the evidence record."""
    await pool.execute(
        "UPDATE evidence SET embedding_id = $1 WHERE id = $2",
        embedding_id,
        evidence_id,
    )


async def update_theme(
    pool: asyncpg.Pool,
    evidence_id: str,
    theme: str,
) -> None:
    """Set the theme label on an evidence record."""
    await pool.execute(
        "UPDATE evidence SET theme = $1 WHERE id = $2",
        theme,
        evidence_id,
    )


async def update_theme_batch(
    pool: asyncpg.Pool,
    evidence_ids: list[str],
    theme: str,
) -> None:
    """Set the theme label on multiple evidence records."""
    await pool.executemany(
        "UPDATE evidence SET theme = $1 WHERE id = $2",
        [(theme, eid) for eid in evidence_ids],
    )
