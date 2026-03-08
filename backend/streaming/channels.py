"""Redis pub/sub channel definitions and publish helper.

Three channels per mission:

  mission:{id}:events   — all UI-facing events (MISSION_STATUS, AGENT_UPDATE,
                           EVIDENCE_FOUND, TIMELINE_EVENT, VOICE_TRANSCRIPT)
  mission:{id}:agents   — agent heartbeats (agent_id, status, timestamp)
  mission:{id}:control  — orchestrator commands (STOP, REDIRECT)

See docs/EVENTS.md for the full payload reference.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


# ── Channel name helpers ──────────────────────────────────────────────────────


def events_channel(mission_id: str) -> str:
    return f"mission:{mission_id}:events"


def agents_channel(mission_id: str) -> str:
    return f"mission:{mission_id}:agents"


def control_channel(mission_id: str) -> str:
    return f"mission:{mission_id}:control"


# ── Publish helper ────────────────────────────────────────────────────────────


async def publish(
    redis: Any,
    mission_id: str,
    event_type: str,
    payload: Any,
) -> None:
    """Publish an event to the mission's events channel.

    The message envelope:
        {"type": "<EVENT_TYPE>", "payload": {...}, "ts": <unix_timestamp>}

    Event types (must match useWebSocket.ts switch cases):
        MISSION_STATUS  — full MissionResponse
        AGENT_UPDATE    — AgentState
        EVIDENCE_FOUND  — EvidenceRecord
        TIMELINE_EVENT  — TimelineEvent
        VOICE_TRANSCRIPT — {role, text, timestamp}
        STATUS_CHANGE   — {status, updated_at}
    """
    msg = json.dumps(
        {"type": event_type, "payload": _serialise(payload), "ts": time.time()}
    )
    channel = events_channel(mission_id)
    try:
        await redis.publish(channel, msg)
    except Exception as exc:
        logger.warning("publish to %s failed: %s", channel, exc)


async def publish_agent_update(redis: Any, mission_id: str, agent_state: dict) -> None:
    """Shorthand to publish an AGENT_UPDATE event."""
    await publish(redis, mission_id, "AGENT_UPDATE", agent_state)


async def publish_timeline_event(redis: Any, mission_id: str, event: dict) -> None:
    """Shorthand to publish a TIMELINE_EVENT event."""
    await publish(redis, mission_id, "TIMELINE_EVENT", event)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _serialise(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO strings for JSON transport."""
    import datetime

    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialise(item) for item in obj]
    return obj
