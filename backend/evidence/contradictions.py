"""Contradiction detection between evidence items — Task 7.5.

Identifies pairs of evidence that contradict each other using
embedding similarity + Nova Lite verification.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import asyncpg
from redis.asyncio import Redis

from evidence.vector_store import VectorStore

logger = logging.getLogger(__name__)

REDIS_CACHE_TTL = 30  # seconds


@dataclass
class Contradiction:
    """A pair of contradicting evidence items."""

    evidence_id_a: str
    evidence_id_b: str
    description: str


async def detect_contradictions(
    mission_id: str,
    db: asyncpg.Pool,
    redis: Redis | None = None,
    store: VectorStore | None = None,
) -> list[Contradiction]:
    """Detect contradictions among evidence for a mission.

    Strategy:
        1. Check Redis cache first (30s TTL).
        2. Fetch all evidence claims for the mission.
        3. If > 5 items, use LLM batch scan (Option B from task spec).
        4. Cache result in Redis.

    Args:
        mission_id: UUID of the mission.
        db: asyncpg connection pool.
        redis: Redis client for caching (optional).
        store: Vector store for embedding-based pre-filtering (optional).

    Returns:
        List of Contradiction objects.
    """
    cache_key = f"mission:{mission_id}:contradictions"

    # Check cache
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached is not None:
                data = json.loads(cached)
                return [Contradiction(**c) for c in data]
        except Exception as exc:
            logger.debug("Cache miss for contradictions: %s", exc)

    # Fetch evidence claims
    rows = await db.fetch(
        """
        SELECT id, claim, summary
        FROM evidence
        WHERE mission_id = $1
        ORDER BY timestamp DESC
        LIMIT 20
        """,
        mission_id,
    )

    if len(rows) < 2:
        return []

    # Use LLM batch scan for contradiction detection
    contradictions = await _llm_batch_detect(rows)

    # Cache result
    if redis is not None:
        try:
            cache_data = json.dumps(
                [
                    {
                        "evidence_id_a": c.evidence_id_a,
                        "evidence_id_b": c.evidence_id_b,
                        "description": c.description,
                    }
                    for c in contradictions
                ]
            )
            await redis.setex(cache_key, REDIS_CACHE_TTL, cache_data)
        except Exception as exc:
            logger.debug("Could not cache contradictions: %s", exc)

    return contradictions


async def _llm_batch_detect(
    rows: list[Any],
) -> list[Contradiction]:
    """Send top evidence claims to Nova Lite to find contradictions.

    Asks the LLM to identify contradicting pairs and return structured JSON.
    """
    claims_text = "\n".join(
        f"[{i}] (id={row['id']}) {row['claim']}" for i, row in enumerate(rows[:10])
    )

    prompt = (
        "Here are evidence claims gathered by research agents. "
        "Identify any pairs that directly contradict each other.\n\n"
        f"Claims:\n{claims_text}\n\n"
        "Return a JSON array of contradicting pairs. Each pair should have:\n"
        '  "a_id": the id of claim A\n'
        '  "b_id": the id of claim B\n'
        '  "reason": brief explanation of the contradiction\n\n'
        "If no contradictions exist, return an empty array: []\n"
        "Return ONLY the JSON array, no other text."
    )

    try:
        from models.lite_client import LiteClient

        client = LiteClient()
        response = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            system=(
                "You are a research analyst checking evidence for contradictions. "
                "Be precise — only flag genuine contradictions, not mere differences "
                "in emphasis or scope. Return valid JSON only."
            ),
            temperature=0.1,
            max_tokens=512,
        )

        # Parse the JSON response
        import re

        cleaned = re.sub(r"```(?:json)?\s*", "", response).replace("```", "").strip()
        pairs = json.loads(cleaned)

        if not isinstance(pairs, list):
            return []

        # Build id lookup for validation
        valid_ids = {str(row["id"]) for row in rows}

        contradictions = []
        for pair in pairs:
            a_id = str(pair.get("a_id", ""))
            b_id = str(pair.get("b_id", ""))
            reason = str(pair.get("reason", "Contradiction detected"))

            if a_id in valid_ids and b_id in valid_ids and a_id != b_id:
                contradictions.append(
                    Contradiction(
                        evidence_id_a=a_id,
                        evidence_id_b=b_id,
                        description=reason,
                    )
                )

        logger.info(
            "Detected %d contradictions from %d claims",
            len(contradictions),
            len(rows),
        )
        return contradictions

    except Exception as exc:
        logger.warning("LLM contradiction detection failed: %s", exc)
        return []
