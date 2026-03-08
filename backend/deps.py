"""FastAPI dependency functions for shared resources."""

from __future__ import annotations

import asyncpg
from fastapi import Request
from redis.asyncio import Redis


def get_db(request: Request) -> asyncpg.Pool:
    return request.app.state.db


def get_redis(request: Request) -> Redis:
    return request.app.state.redis
