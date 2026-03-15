"""Mission Control — FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from evidence.dlq import dlq_worker
from logging_config import configure_logging
from metrics import flush as flush_metrics

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    json_logs = not settings.demo_mode  # Pretty console in demo, JSON in prod
    configure_logging(level=settings.log_level, json_output=json_logs)

    # asyncpg needs a plain postgresql:// DSN (strips SQLAlchemy prefix).
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    app.state.db = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=False)
    logger.info("DB pool and Redis connected")

    # Start DLQ background worker for retrying failed evidence ingestion.
    dlq_task = asyncio.create_task(dlq_worker(app.state.redis, app.state.db))

    # Initialise X-Ray tracing in non-demo mode.
    if not settings.demo_mode:
        from tracing import init_tracing

        init_tracing()

    yield

    # Flush any remaining buffered CloudWatch metrics on shutdown.
    await flush_metrics()

    dlq_task.cancel()
    try:
        await dlq_task
    except asyncio.CancelledError:
        pass

    await app.state.db.close()
    await app.state.redis.aclose()
    logger.info("DB pool and Redis closed")


app = FastAPI(title="Mission Control", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# X-Ray middleware — adds a segment per request (disabled in demo mode).
if not settings.demo_mode:
    from tracing import XRayMiddleware

    app.add_middleware(XRayMiddleware)


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Routers (mounted in build order) ──────────────────────────────────────────

from missions.router import router as missions_router  # noqa: E402

app.include_router(missions_router)

from evidence.router import router as evidence_router  # noqa: E402

app.include_router(evidence_router)

from streaming.ws_relay import router as ws_relay_router  # noqa: E402

app.include_router(ws_relay_router)

from gateway.voice_gateway import router as voice_router  # noqa: E402

app.include_router(voice_router)

from routers.internal import router as internal_router  # noqa: E402

app.include_router(internal_router)

if settings.demo_mode:
    from routers.demo import router as demo_router  # noqa: E402

    app.include_router(demo_router)
