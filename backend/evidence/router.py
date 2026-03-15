"""FastAPI router — Evidence ingest and list endpoints."""

from __future__ import annotations

import logging
from typing import Optional

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from redis.asyncio import Redis

from deps import get_db, get_redis
from evidence import repository
from evidence.schemas import EvidenceIngest, EvidenceResponse
from evidence.scoring import compute_confidence

logger = logging.getLogger(__name__)

router = APIRouter(tags=["evidence"])


async def _upload_screenshot_background(
    evidence_id: str,
    mission_id: str,
    base64_data: str,
    db: asyncpg.Pool,
) -> None:
    """Background task: decode + upload screenshot to S3, update DB."""
    try:
        from evidence.screenshot import upload_screenshot

        s3_key = await upload_screenshot(evidence_id, mission_id, base64_data)
        await repository.update_screenshot_key(db, evidence_id, s3_key)
        logger.info("Screenshot uploaded for evidence %s → %s", evidence_id, s3_key)
    except Exception as exc:
        logger.error("Screenshot upload failed for evidence %s: %s", evidence_id, exc)


@router.post("/evidence", response_model=EvidenceResponse, status_code=201)
async def ingest_evidence(
    body: EvidenceIngest,
    background_tasks: BackgroundTasks,
    db: asyncpg.Pool = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> EvidenceResponse:
    """Ingest a new evidence item; publishes EVIDENCE_FOUND to Redis pub/sub."""
    # Compute confidence from source heuristics (synchronous, fast)
    confidence = compute_confidence(body.source_url, body.snippet)

    try:
        row = await repository.insert_evidence(
            db,
            mission_id=body.mission_id,
            agent_id=body.agent_id,
            claim=body.claim,
            summary=body.summary,
            source_url=body.source_url,
            snippet=body.snippet,
            confidence=confidence,
            novelty=body.novelty,
            theme=body.theme,
            screenshot_s3_key=body.screenshot_s3_key,
        )
    except asyncpg.ForeignKeyViolationError:
        raise HTTPException(
            status_code=422,
            detail="mission_id references a mission that does not exist",
        )

    # Kick off screenshot upload as a background task (non-blocking)
    if body.screenshot_base64:
        background_tasks.add_task(
            _upload_screenshot_background,
            row["id"],
            body.mission_id,
            body.screenshot_base64,
            db,
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

    # Generate presigned screenshot URLs on-the-fly
    results = []
    for r in rows:
        resp = EvidenceResponse(**r)
        if r.get("screenshot_s3_key"):
            try:
                from evidence.screenshot import get_screenshot_url

                resp.screenshot_url = get_screenshot_url(r["screenshot_s3_key"])
            except Exception as exc:
                logger.warning("Could not generate screenshot URL: %s", exc)
        results.append(resp)

    return results
