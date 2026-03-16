"""Internal endpoints — DLQ monitoring, flush, and briefing delivery."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from evidence.dlq import flush_dlq, get_dlq_count, get_dlq_items
from streaming.channels import publish

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


class DeliverBriefingRequest(BaseModel):
    mission_id: str
    briefing_text: str


@router.post("/deliver-briefing")
async def deliver_briefing(body: DeliverBriefingRequest, request: Request):
    """Accept a synthesised briefing and publish it to the mission channel.

    The synthesis pipeline calls this endpoint so that any connected WebSocket
    client (War Room UI, Voice Gateway) receives the final briefing.
    """
    redis = request.app.state.redis
    await publish(
        redis,
        body.mission_id,
        "BRIEFING_READY",
        {"mission_id": body.mission_id, "briefing_text": body.briefing_text},
    )
    logger.info("Briefing delivered for mission %s via internal endpoint", body.mission_id)
    return {"status": "accepted", "mission_id": body.mission_id}


@router.get("/dlq/count")
async def dlq_count(request: Request):
    """Return the current DLQ size."""
    redis = request.app.state.redis
    count = await get_dlq_count(redis)
    return {"count": count}


@router.get("/dlq/items")
async def dlq_list(request: Request, limit: int = 20):
    """Peek at DLQ items."""
    redis = request.app.state.redis
    items = await get_dlq_items(redis, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/dlq/flush")
async def dlq_flush(request: Request):
    """Retry all DLQ items immediately."""
    redis = request.app.state.redis
    db = request.app.state.db
    result = await flush_dlq(redis, db)
    return result
