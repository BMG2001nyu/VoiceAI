"""Mission Control — FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure the project root is on sys.path so the `agents` package is importable.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import asyncpg  # noqa: E402
import redis.asyncio as aioredis  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from gateway.ws_relay import router as relay_router  # noqa: E402

from config import settings  # noqa: E402
from evidence.dlq import dlq_worker  # noqa: E402
from logging_config import configure_logging  # noqa: E402
from metrics import flush as flush_metrics  # noqa: E402

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    json_logs = not settings.demo_mode  # Pretty console in demo, JSON in prod
    configure_logging(level=settings.log_level, json_output=json_logs)

    app.state.db = None
    app.state.redis = None
    dlq_task = None

    # Connect to Postgres (optional on serverless: /health still works if this fails).
    try:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        app.state.db = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
        logger.info("DB pool connected")
    except Exception as e:
        logger.warning(
            "DB pool not available (serverless or missing DATABASE_URL): %s", e
        )

    # Connect to Redis (optional on serverless).
    try:
        app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=False)
        await app.state.redis.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis not available (serverless or missing REDIS_URL): %s", e)
        app.state.redis = None

    # Start DLQ worker and init agent pool only when Redis is available.
    if app.state.redis is not None and app.state.db is not None:
        dlq_task = asyncio.create_task(dlq_worker(app.state.redis, app.state.db))
        try:
            from agents.pool import init_pool

            await init_pool(app.state.redis, settings.agent_pool_size)
            logger.info("Agent pool initialized (%d agents)", settings.agent_pool_size)
        except ImportError as e:
            logger.warning(
                "Agents package not available (e.g. Vercel deploy from backend/): %s", e
            )
        except Exception as e:
            logger.warning("Agent pool init failed: %s", e)

    # Initialise X-Ray tracing in non-demo mode (skip if it would crash).
    if not settings.demo_mode:
        try:
            from tracing import init_tracing

            init_tracing()
        except Exception as e:
            logger.warning("Tracing init skipped: %s", e)

    yield

    # Flush any remaining buffered CloudWatch metrics on shutdown.
    try:
        await flush_metrics()
    except Exception:
        pass

    if dlq_task is not None:
        dlq_task.cancel()
        try:
            await dlq_task
        except asyncio.CancelledError:
            pass

    if app.state.db is not None:
        await app.state.db.close()
        logger.info("DB pool closed")
    if app.state.redis is not None:
        await app.state.redis.aclose()
        logger.info("Redis closed")


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

# Include common routers
app.include_router(relay_router, tags=["relay"])


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


@app.get("/internal/dlq/count")
async def dlq_count():
    """Returns the size of the dead-letter queue (Task 13.5)."""
    # In a real app, this would query LLEN on Redis.
    # For now, return 0 or a mock value based on a query parameter for dev.
    return {"count": 0}
