"""FastAPI router — Mission CRUD endpoints."""

from __future__ import annotations

import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis

from deps import get_db, get_redis
from missions.schemas import MissionCreate, MissionResponse, MissionUpdate
from missions import repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/missions", tags=["missions"])


async def _publish_status_change(redis: Redis, mission: dict) -> None:
    """Publish a STATUS_CHANGE event so the WS relay forwards it to the browser."""
    # Import here to avoid a circular dependency before streaming/ exists.
    try:
        from streaming.channels import publish

        await publish(redis, mission["id"], "MISSION_STATUS", mission)
    except Exception:
        logger.warning("Could not publish STATUS_CHANGE; streaming not wired yet")


@router.post("", response_model=MissionResponse, status_code=201)
async def create_mission(
    body: MissionCreate,
    db: asyncpg.Pool = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MissionResponse:
    """Create a mission, decompose it into tasks via Nova Lite, return the mission."""
    from config import settings
    from models.lite_client import LiteClient

    mission = await repository.create_mission(db, body.objective)
    mission_id = mission["id"]

    try:
        client = LiteClient(api_key=settings.nova_api_key)
        task_graph = await client.plan_tasks(body.objective)
    except Exception as exc:
        logger.error("plan_tasks failed for mission %s: %s", mission_id, exc)
        task_graph = []

    mission = await repository.set_task_graph(db, mission_id, task_graph)
    await _publish_status_change(redis, mission)
    return MissionResponse(**mission)


@router.get("/{mission_id}", response_model=MissionResponse)
async def get_mission(
    mission_id: str,
    db: asyncpg.Pool = Depends(get_db),
) -> MissionResponse:
    mission = await repository.get_mission(db, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return MissionResponse(**mission)


@router.patch("/{mission_id}", response_model=MissionResponse)
async def update_mission(
    mission_id: str,
    body: MissionUpdate,
    db: asyncpg.Pool = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MissionResponse:
    # Valid forward transitions — terminal states (COMPLETE, FAILED) are immutable.
    _VALID_TRANSITIONS: dict[str, set[str]] = {
        "PENDING": {"ACTIVE", "FAILED"},
        "ACTIVE": {"SYNTHESIZING", "FAILED"},
        "SYNTHESIZING": {"COMPLETE", "FAILED"},
        "COMPLETE": set(),
        "FAILED": set(),
    }
    valid_statuses = set(_VALID_TRANSITIONS.keys())
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    current = await repository.get_mission(db, mission_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Mission not found")

    allowed = _VALID_TRANSITIONS.get(current["status"], set())
    if body.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot transition from {current['status']} to {body.status}. "
                f"Allowed next states: {sorted(allowed) or ['none (terminal)']}"
            ),
        )

    mission = await repository.update_mission_status(db, mission_id, body.status)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    await _publish_status_change(redis, mission)
    return MissionResponse(**mission)
