"""FastAPI dependency functions for shared resources."""

from __future__ import annotations

import asyncpg
from fastapi import HTTPException, Request
from redis.asyncio import Redis


def get_db(request: Request) -> asyncpg.Pool:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Set DATABASE_URL and redeploy, or run backend locally with Docker Compose.",
        )
    return db


def get_redis(request: Request) -> Redis:
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(
            status_code=503,
            detail="Redis not available. Set REDIS_URL and redeploy, or run backend locally with Docker Compose.",
        )
    return redis
