"""Demo reset endpoint — only mounted when DEMO_MODE=true.

POST /demo/reset wipes all mission state, evidence, and Redis keys.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset", status_code=204)
async def demo_reset(
    request: Request,
    x_api_key: str = Header(default=""),
) -> None:
    """Wipe all demo state: missions, evidence, tasks, and Redis keys."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    db = request.app.state.db
    redis = request.app.state.redis

    # Clear Postgres tables (order matters for FK constraints)
    async with db.acquire() as conn:
        await conn.execute("DELETE FROM evidence")
        await conn.execute("DELETE FROM tasks")
        await conn.execute("DELETE FROM missions")

    # Clear Redis mission and agent keys
    keys: list[bytes] = []

    cursor = b"0"
    while True:
        cursor, batch = await redis.scan(cursor, match="mission:*", count=100)
        keys.extend(batch)
        if cursor == b"0" or cursor == 0:
            break

    cursor = b"0"
    while True:
        cursor, batch = await redis.scan(cursor, match="agent:*", count=100)
        keys.extend(batch)
        if cursor == b"0" or cursor == 0:
            break

    # Also clear DLQ
    keys.append(b"mission-control:dlq")

    if keys:
        await redis.delete(*keys)

    logger.info(
        "Demo reset complete: cleared Postgres tables and %d Redis keys", len(keys)
    )
