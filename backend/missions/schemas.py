"""Pydantic schemas for missions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MissionCreate(BaseModel):
    objective: str


class MissionUpdate(BaseModel):
    status: str


class MissionResponse(BaseModel):
    id: str
    objective: str
    status: str
    task_graph: list[Any] | None = None
    created_at: datetime
    updated_at: datetime
    briefing: str | None = None

    model_config = {"from_attributes": True}
