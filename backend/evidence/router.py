"""FastAPI router — Evidence ingest and list endpoints."""

from __future__ import annotations

import logging
from typing import Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis

from deps import get_db, get_redis
from evidence.schemas import EvidenceIngest, EvidenceResponse
from evidence import repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["evidence"])


@router.post("/evidence", response_model=EvidenceResponse, status_code=201)
async def ingest_evidence(
    body: EvidenceIngest,
    db: asyncpg.Pool = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> EvidenceResponse:
    """Ingest a new evidence item; publishes EVIDENCE_FOUND to Redis pub/sub."""
    try:
        row = await repository.insert_evidence(
            db,
            mission_id=body.mission_id,
            agent_id=body.agent_id,
            claim=body.claim,
            summary=body.summary,
            source_url=body.source_url,
            snippet=body.snippet,
            confidence=body.confidence,
            novelty=body.novelty,
            theme=body.theme,
            screenshot_s3_key=body.screenshot_s3_key,
        )
    except asyncpg.ForeignKeyViolationError:
        raise HTTPException(
            status_code=422,
            detail="mission_id references a mission that does not exist",
        )

    # Publish to Redis so the WS relay forwards it to all War Room browsers.
    try:
        from streaming.channels import publish

        # Serialise datetime to ISO string and add created_at alias so the
        # frontend EvidenceRecord type (which uses created_at) works correctly.
        payload = dict(row)
        ts_iso = payload["timestamp"].isoformat()
        payload["timestamp"] = ts_iso
        payload["created_at"] = ts_iso  # alias expected by frontend EvidenceRecord
        await publish(redis, body.mission_id, "EVIDENCE_FOUND", payload)
    except Exception as exc:
        logger.warning("Could not publish EVIDENCE_FOUND: %s", exc)

    return EvidenceResponse(**row)


@router.get("/missions/{mission_id}/evidence", response_model=list[EvidenceResponse])
async def list_evidence(
    mission_id: str,
    theme: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: asyncpg.Pool = Depends(get_db),
) -> list[EvidenceResponse]:
    """List evidence for a mission with optional theme filter and pagination."""
    rows = await repository.list_evidence(
        db, mission_id, theme=theme, limit=limit, offset=offset
    )
    return [EvidenceResponse(**r) for r in rows]
