"""Spoken briefing delivery via Nova Sonic — Task 12.3.

After synthesis generates the briefing text (Task 12.2),
this module triggers the Voice Gateway to deliver it as audio.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def deliver_spoken_briefing(
    mission_id: str,
    briefing_text: str,
) -> bool:
    """Send briefing text to the Voice Gateway for spoken delivery.

    Posts to the internal endpoint that Chinmay's gateway exposes.
    The gateway streams audio to the connected WebSocket client.

    Args:
        mission_id: UUID of the mission.
        briefing_text: The generated briefing text.

    Returns:
        True if delivery was accepted, False otherwise.
    """
    gateway_url = f"{settings.backend_url}/internal/deliver-briefing"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                gateway_url,
                json={
                    "mission_id": mission_id,
                    "briefing_text": briefing_text,
                },
            )

        if response.status_code in (200, 202):
            logger.info("Spoken briefing accepted for mission %s", mission_id)
            return True

        logger.warning(
            "Spoken briefing delivery returned %d for mission %s",
            response.status_code,
            mission_id,
        )
        return False

    except httpx.ConnectError:
        logger.warning(
            "Voice Gateway not reachable — spoken briefing skipped for mission %s",
            mission_id,
        )
        return False
    except Exception as exc:
        logger.error("Spoken briefing delivery failed: %s", exc)
        return False


async def run_synthesis_pipeline(
    mission_id: str,
    db: Any,
    redis: Any = None,
) -> str:
    """Full synthesis pipeline: cluster -> label -> briefing -> speak.

    Convenience function that orchestrates Tasks 12.1 -> 12.2 -> 12.3.

    Args:
        mission_id: UUID of the mission.
        db: asyncpg connection pool.
        redis: Redis client (optional, for contradiction cache).

    Returns:
        The generated briefing text.
    """
    from synthesis.pre_synthesis import prepare_evidence_clusters
    from synthesis.briefing import generate_briefing
    from evidence.contradictions import detect_contradictions

    # Step 1: Cluster + label evidence (Task 12.1)
    cluster_summaries = await prepare_evidence_clusters(mission_id, db)

    # Step 2: Detect contradictions (Task 7.5)
    contras = await detect_contradictions(mission_id, db, redis)
    contra_dicts = [
        {
            "evidence_id_a": c.evidence_id_a,
            "evidence_id_b": c.evidence_id_b,
            "description": c.description,
        }
        for c in contras
    ]

    # Step 3: Fetch mission objective
    row = await db.fetchrow(
        "SELECT objective FROM missions WHERE id = $1",
        mission_id,
    )
    objective = row["objective"] if row else "Unknown objective"

    # Step 4: Generate briefing (Task 12.2)
    briefing_text = await generate_briefing(
        mission_id=mission_id,
        objective=objective,
        cluster_summaries=cluster_summaries,
        contradictions=contra_dicts,
        db=db,
        redis=redis,
    )

    # Step 5: Deliver spoken briefing (Task 12.3)
    await deliver_spoken_briefing(mission_id, briefing_text)

    return briefing_text
