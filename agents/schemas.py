"""Shared schemas for the agent command and control system."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CommandType(StrEnum):
    """Types of commands the orchestrator can send to agents."""
    ASSIGN = "ASSIGN"
    REDIRECT = "REDIRECT"
    STOP = "STOP"


class AgentCommand(BaseModel):
    """A command sent from the orchestrator to an agent via Redis."""
    command_type: CommandType
    agent_id: str
    task_id: str | None = None
    mission_id: str | None = None
    objective: str = ""
    agent_type: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)


class AgentStatus(StrEnum):
    """Agent lifecycle states."""
    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    BROWSING = "BROWSING"
    REPORTING = "REPORTING"
