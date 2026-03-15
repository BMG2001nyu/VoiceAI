"""Dead-letter queue for failed evidence ingestion.

Failed POST /evidence attempts are captured in a Redis list for retry.
A background worker retries items with exponential backoff (max 3 attempts).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

DLQ_KEY = "mission-control:dlq"
MAX_RETRIES = 3
RETRY_INTERVAL_S = 30


async def push_to_dlq(redis: Any, payload: dict, error: str) -> None:
    """Push a failed evidence payload to the dead-letter queue.

    Args:
        redis: aioredis client.
        payload: The original EvidenceIngest dict that failed.
        error: Error message describing the failure.
    """
    item = {
        "payload": payload,
        "error": error,
        "attempts": 0,
        "first_failed_at": time.time(),
        "last_attempted_at": time.time(),
    }
    await redis.lpush(DLQ_KEY, json.dumps(item))
    logger.warning("DLQ: pushed failed evidence (error=%s)", error)


async def get_dlq_count(redis: Any) -> int:
    """Return the number of items in the DLQ."""
    count = await redis.llen(DLQ_KEY)
    return count or 0


async def get_dlq_items(redis: Any, limit: int = 20) -> list[dict]:
    """Peek at DLQ items without removing them."""
    raw_items = await redis.lrange(DLQ_KEY, 0, limit - 1)
    items = []
    for raw in raw_items:
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            items.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return items


async def flush_dlq(redis: Any, db: Any) -> dict[str, int]:
    """Retry all DLQ items immediately.

    Returns:
        Dict with counts: {"retried": N, "failed": M, "discarded": K}
    """
    from evidence.repository import insert_evidence

    count = await redis.llen(DLQ_KEY)
    if not count:
        return {"retried": 0, "failed": 0, "discarded": 0}

    retried = 0
    failed = 0
    discarded = 0

    for _ in range(count):
        raw = await redis.rpop(DLQ_KEY)
        if raw is None:
            break

        if isinstance(raw, bytes):
            raw = raw.decode()

        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            discarded += 1
            continue

        payload = item.get("payload", {})
        attempts = item.get("attempts", 0) + 1

        if attempts > MAX_RETRIES:
            logger.error(
                "DLQ: discarding after %d attempts: %s",
                attempts,
                payload.get("claim", "?")[:80],
            )
            discarded += 1
            continue

        try:
            await insert_evidence(
                db,
                mission_id=payload["mission_id"],
                agent_id=payload["agent_id"],
                claim=payload["claim"],
                summary=payload["summary"],
                source_url=payload["source_url"],
                snippet=payload.get("snippet", ""),
                confidence=payload.get("confidence", 0.5),
                novelty=payload.get("novelty", 1.0),
                theme=payload.get("theme"),
                screenshot_s3_key=payload.get("screenshot_s3_key"),
            )
            retried += 1
            logger.info("DLQ: retried successfully (attempt %d)", attempts)
        except Exception as exc:
            failed += 1
            item["attempts"] = attempts
            item["last_attempted_at"] = time.time()
            item["error"] = str(exc)
            await redis.lpush(DLQ_KEY, json.dumps(item))
            logger.warning("DLQ: retry failed (attempt %d): %s", attempts, exc)

    result = {"retried": retried, "failed": failed, "discarded": discarded}
    logger.info("DLQ flush result: %s", result)
    return result


async def dlq_worker(redis: Any, db: Any) -> None:
    """Background worker that retries DLQ items every RETRY_INTERVAL_S.

    Runs indefinitely until cancelled.
    """
    logger.info("DLQ worker started (interval=%ds)", RETRY_INTERVAL_S)
    try:
        while True:
            await asyncio.sleep(RETRY_INTERVAL_S)
            count = await get_dlq_count(redis)
            if count > 0:
                logger.info("DLQ worker: %d items pending, flushing...", count)
                await flush_dlq(redis, db)
    except asyncio.CancelledError:
        logger.info("DLQ worker stopped")
