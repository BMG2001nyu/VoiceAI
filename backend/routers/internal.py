"""Internal endpoints — DLQ monitoring and flush."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from evidence.dlq import flush_dlq, get_dlq_count, get_dlq_items

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


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
