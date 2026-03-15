"""Tests for the orchestrator context packet builder and planning loop."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.context_packet import build_context_packet, _elapsed_seconds
from orchestrator.planning_loop import run_planning_loop

# ── Fixtures ─────────────────────────────────────────────────────────────────


def _make_mission(
    mission_id: str = "test-mission-001",
    objective: str = "Research Sequoia Capital",
    status: str = "ACTIVE",
    task_graph: list[dict] | None = None,
) -> dict[str, Any]:
    """Build a fake mission record."""
    if task_graph is None:
        task_graph = [
            {
                "id": "task-1",
                "description": "Check official site",
                "agent_type": "OFFICIAL_SITE",
                "priority": 9,
                "status": "PENDING",
                "dependencies": [],
            },
            {
                "id": "task-2",
                "description": "Search news",
                "agent_type": "NEWS_BLOG",
                "priority": 7,
                "status": "DONE",
                "dependencies": [],
            },
        ]
    return {
        "id": mission_id,
        "objective": objective,
        "status": status,
        "task_graph": task_graph,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "briefing": None,
    }


def _make_evidence(count: int = 3, theme: str = "technology") -> list[dict[str, Any]]:
    """Build a list of fake evidence records."""
    return [
        {
            "id": f"ev-{i}",
            "mission_id": "test-mission-001",
            "agent_id": f"agent_{i % 6}",
            "claim": f"Claim number {i}",
            "summary": f"Summary {i}",
            "source_url": f"https://example.com/{i}",
            "snippet": f"Snippet {i}",
            "confidence": 0.8,
            "novelty": 1.0,
            "theme": theme if i % 2 == 0 else None,
            "screenshot_s3_key": None,
            "embedding_id": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        for i in range(count)
    ]


def _make_redis_mock(pool_size: int = 6) -> AsyncMock:
    """Build a mock Redis client with agent state."""
    redis = AsyncMock(spec=["hget", "hgetall", "hset", "get", "publish", "pipeline"])

    # Agent state lookup
    async def _hgetall(key: str) -> dict[bytes, bytes]:
        return {
            b"status": b"IDLE",
            b"task_id": b"",
            b"mission_id": b"",
            b"agent_type": b"",
            b"session_id": b"",
            b"last_heartbeat": str(time.time()).encode(),
        }

    async def _hget(key: str, field: str) -> bytes | None:
        if field == "status":
            return b"IDLE"
        return b""

    async def _get(key: str) -> bytes | None:
        if "contradictions" in key:
            return json.dumps([]).encode()
        return None

    redis.hgetall = AsyncMock(side_effect=_hgetall)
    redis.hget = AsyncMock(side_effect=_hget)
    redis.get = AsyncMock(side_effect=_get)
    redis.publish = AsyncMock(return_value=1)

    return redis


# ── Context Packet Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_context_packet_success():
    """Context packet builds correctly with valid mission and evidence."""
    mission = _make_mission()
    evidence = _make_evidence(4)

    db = AsyncMock()
    redis = _make_redis_mock()

    with (
        patch("orchestrator.context_packet.get_mission", return_value=mission),
        patch("orchestrator.context_packet.list_evidence", return_value=evidence),
    ):
        packet = await build_context_packet("test-mission-001", db, redis)

    assert packet["mission_id"] == "test-mission-001"
    assert packet["objective"] == "Research Sequoia Capital"
    assert packet["status"] == "ACTIVE"
    assert packet["total_tasks"] == 2
    assert packet["evidence_count"] == 4
    assert isinstance(packet["elapsed_sec"], float)
    assert isinstance(packet["task_summary"], dict)
    assert "PENDING" in packet["task_summary"]
    assert "DONE" in packet["task_summary"]
    assert len(packet["available_tasks"]) == 1  # task-1 is PENDING with no deps
    assert isinstance(packet["agent_pool"], dict)
    assert len(packet["agents"]) == 6


@pytest.mark.asyncio
async def test_build_context_packet_mission_not_found():
    """Context packet returns error dict when mission does not exist."""
    db = AsyncMock()
    redis = _make_redis_mock()

    with patch("orchestrator.context_packet.get_mission", return_value=None):
        packet = await build_context_packet("nonexistent", db, redis)

    assert packet["mission_id"] == "nonexistent"
    assert packet["error"] == "mission_not_found"


@pytest.mark.asyncio
async def test_build_context_packet_empty_evidence():
    """Context packet handles empty evidence list gracefully."""
    mission = _make_mission(task_graph=[])
    db = AsyncMock()
    redis = _make_redis_mock()

    with (
        patch("orchestrator.context_packet.get_mission", return_value=mission),
        patch("orchestrator.context_packet.list_evidence", return_value=[]),
    ):
        packet = await build_context_packet("test-mission-001", db, redis)

    assert packet["evidence_count"] == 0
    assert packet["evidence_by_theme"] == {}
    assert packet["total_tasks"] == 0
    assert packet["available_tasks"] == []


@pytest.mark.asyncio
async def test_build_context_packet_with_contradictions():
    """Context packet reads contradiction count from Redis cache."""
    mission = _make_mission()
    db = AsyncMock()
    redis = _make_redis_mock()

    # Override get to return cached contradictions
    contras = [
        {"evidence_id_a": "a", "evidence_id_b": "b", "description": "test"},
    ]

    async def _get_with_contras(key: str) -> bytes | None:
        if "contradictions" in key:
            return json.dumps(contras).encode()
        return None

    redis.get = AsyncMock(side_effect=_get_with_contras)

    with (
        patch("orchestrator.context_packet.get_mission", return_value=mission),
        patch("orchestrator.context_packet.list_evidence", return_value=[]),
    ):
        packet = await build_context_packet("test-mission-001", db, redis)

    assert packet["contradiction_count"] == 1


def test_elapsed_seconds_with_datetime():
    """_elapsed_seconds computes correct delta from datetime."""
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    elapsed = _elapsed_seconds(past)
    assert elapsed > 0


def test_elapsed_seconds_with_none():
    """_elapsed_seconds returns 0 for None input."""
    assert _elapsed_seconds(None) == 0.0


# ── Planning Loop Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_planning_loop_stops_when_should_stop():
    """Planning loop breaks when should_stop returns True."""
    mission = _make_mission()
    db = AsyncMock()
    redis = _make_redis_mock()

    cycle_count = 0

    async def _mock_should_stop(mid, elapsed, pool, **kw):
        nonlocal cycle_count
        cycle_count += 1
        return True, "Time budget exceeded"

    with (
        patch("orchestrator.planning_loop.get_mission", return_value=mission),
        patch(
            "orchestrator.planning_loop.build_context_packet",
            return_value={
                "mission_id": "test-mission-001",
                "elapsed_sec": 50.0,
                "agents": [],
            },
        ),
        patch("orchestrator.planning_loop.should_stop", side_effect=_mock_should_stop),
        patch("orchestrator.planning_loop.update_mission_status", return_value=mission),
        patch("orchestrator.planning_loop.publish_timeline_event", return_value=None),
        patch("orchestrator.planning_loop.settings", MagicMock(agent_pool_size=6)),
    ):
        await run_planning_loop("test-mission-001", db, redis)

    assert cycle_count == 1


@pytest.mark.asyncio
async def test_planning_loop_assigns_tasks():
    """Planning loop assigns tasks when available tasks and idle agents exist."""
    mission = _make_mission()
    db = AsyncMock()
    redis = _make_redis_mock()

    from orchestrator.assignment import AssignAction

    assign_result = [
        AssignAction(
            agent_id="agent_0",
            task_id="task-1",
            objective="Check official site",
            agent_type="OFFICIAL_SITE",
            constraints={"timeout_s": 120},
        )
    ]

    call_count = 0

    async def _mock_should_stop(mid, elapsed, pool, **kw):
        nonlocal call_count
        call_count += 1
        # Stop after first cycle
        return call_count > 1, "All tasks completed" if call_count > 1 else ""

    with (
        patch("orchestrator.planning_loop.get_mission", return_value=mission),
        patch(
            "orchestrator.planning_loop.build_context_packet",
            return_value={
                "mission_id": "test-mission-001",
                "elapsed_sec": 5.0,
                "agents": [],
            },
        ),
        patch("orchestrator.planning_loop.should_stop", side_effect=_mock_should_stop),
        patch(
            "orchestrator.planning_loop.detect_reallocation_opportunities",
            return_value=[],
        ),
        patch("orchestrator.planning_loop.assign_tasks", return_value=assign_result),
        patch(
            "orchestrator.planning_loop.dispatch_commands", return_value=1
        ) as mock_dispatch,
        patch("orchestrator.planning_loop.publish_timeline_event", return_value=None),
        patch("orchestrator.planning_loop.update_mission_status", return_value=mission),
        patch("orchestrator.planning_loop.settings", MagicMock(agent_pool_size=6)),
        patch("orchestrator.planning_loop.asyncio.sleep", return_value=None),
    ):
        await run_planning_loop("test-mission-001", db, redis)

    mock_dispatch.assert_called_once_with(assign_result, redis, "test-mission-001")


@pytest.mark.asyncio
async def test_planning_loop_handles_missing_mission():
    """Planning loop exits cleanly when mission is not found."""
    db = AsyncMock()
    redis = _make_redis_mock()

    with (
        patch("orchestrator.planning_loop.get_mission", return_value=None),
        patch("orchestrator.planning_loop.settings", MagicMock(agent_pool_size=6)),
    ):
        # Should complete without raising
        await run_planning_loop("nonexistent", db, redis)


@pytest.mark.asyncio
async def test_planning_loop_skips_non_active_mission():
    """Planning loop breaks when mission is in a terminal state."""
    mission = _make_mission(status="COMPLETE")
    db = AsyncMock()
    redis = _make_redis_mock()

    with (
        patch("orchestrator.planning_loop.get_mission", return_value=mission),
        patch("orchestrator.planning_loop.settings", MagicMock(agent_pool_size=6)),
    ):
        await run_planning_loop("test-mission-001", db, redis)


@pytest.mark.asyncio
async def test_planning_loop_survives_transient_error():
    """Planning loop continues after a transient exception in a cycle."""
    mission = _make_mission()
    db = AsyncMock()
    redis = _make_redis_mock()

    call_count = 0

    async def _mock_build_context(mid, pool, red, ps=6):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Redis transient failure")
        return {
            "mission_id": mid,
            "elapsed_sec": 50.0,
            "agents": [],
        }

    async def _mock_should_stop(mid, elapsed, pool, **kw):
        return True, "Time budget exceeded"

    with (
        patch("orchestrator.planning_loop.get_mission", return_value=mission),
        patch(
            "orchestrator.planning_loop.build_context_packet",
            side_effect=_mock_build_context,
        ),
        patch("orchestrator.planning_loop.should_stop", side_effect=_mock_should_stop),
        patch("orchestrator.planning_loop.update_mission_status", return_value=mission),
        patch("orchestrator.planning_loop.publish_timeline_event", return_value=None),
        patch("orchestrator.planning_loop.settings", MagicMock(agent_pool_size=6)),
        patch("orchestrator.planning_loop.asyncio.sleep", return_value=None),
    ):
        await run_planning_loop("test-mission-001", db, redis)

    # The loop survived the first error and ran a second cycle
    assert call_count == 2
