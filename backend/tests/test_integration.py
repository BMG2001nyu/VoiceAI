"""Integration tests for the full Mission Control API.

Tests cover:
  - Mission CRUD (create, read, state machine)
  - Evidence ingest + list (REST + published payload shape)
  - WebSocket relay (receives Redis events)
  - State-machine enforcement (valid and invalid transitions)
  - Evidence created_at alias in published payload

All tests use the ASGI test client and mock the DB/Redis pool so no live
services are needed (except where explicitly noted in the docstring).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from main import app

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_mission(
    *,
    id: str | None = None,
    objective: str = "Test objective",
    status: str = "PENDING",
    task_graph=None,
    briefing: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "id": id or str(uuid.uuid4()),
        "objective": objective,
        "status": status,
        "task_graph": task_graph or [],
        "created_at": now,
        "updated_at": now,
        "briefing": briefing,
    }


def _make_evidence(
    *,
    id: str | None = None,
    mission_id: str | None = None,
    agent_id: str = "agent_0",
    claim: str = "Test claim",
    summary: str = "Test summary",
    source_url: str = "https://example.com",
    snippet: str = "Test snippet",
    confidence: float = 0.9,
    novelty: float = 1.0,
    theme: str | None = "Test Theme",
    screenshot_s3_key: str | None = None,
) -> dict[str, Any]:
    return {
        "id": id or str(uuid.uuid4()),
        "mission_id": mission_id or str(uuid.uuid4()),
        "agent_id": agent_id,
        "claim": claim,
        "summary": summary,
        "source_url": source_url,
        "snippet": snippet,
        "confidence": confidence,
        "novelty": novelty,
        "theme": theme,
        "screenshot_s3_key": screenshot_s3_key,
        "timestamp": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_app_state(mission: dict | None = None, evidence_list: list | None = None):
    """Return a mock app.state with a pool and redis that answer simple queries."""
    mission = mission or _make_mission()
    evidence_list = evidence_list or []

    # asyncpg pool mock
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=_as_record(mission))
    pool.fetch = AsyncMock(return_value=[_as_record(e) for e in evidence_list])

    # redis mock
    redis = AsyncMock()
    redis.publish = AsyncMock(return_value=1)

    state = MagicMock()
    state.db = pool
    state.redis = redis
    return state


def _as_record(d: dict) -> MagicMock:
    """Return a MagicMock that behaves like an asyncpg.Record (dict-like)."""
    rec = MagicMock()
    rec.__iter__ = lambda self: iter(d.items())
    rec.items = lambda: d.items()
    rec.keys = lambda: d.keys()
    rec.values = lambda: d.values()
    rec.get = d.get
    rec.__getitem__ = lambda self, k: d[k]
    return rec


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Mission CRUD
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_mission():
    """POST /missions → 201 with id, status ACTIVE, task_graph from plan_tasks."""
    mission_id = str(uuid.uuid4())
    pending = _make_mission(id=mission_id, status="PENDING")
    active = _make_mission(id=mission_id, status="ACTIVE", task_graph=[{"task": 1}])

    pool = AsyncMock()
    # first call: create_mission; second call: set_task_graph
    pool.fetchrow = AsyncMock(side_effect=[_as_record(pending), _as_record(active)])

    redis = AsyncMock()
    redis.publish = AsyncMock(return_value=1)

    app.state.db = pool
    app.state.redis = redis

    mock_tasks = [
        {
            "description": "task1",
            "agent_type": "NEWS_BLOG",
            "priority": 5,
            "dependencies": [],
        }
    ]

    with patch(
        "models.lite_client.LiteClient.plan_tasks",
        new=AsyncMock(return_value=mock_tasks),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/missions", json={"objective": "Test"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == mission_id
    assert data["status"] == "ACTIVE"
    assert isinstance(data["task_graph"], list)


@pytest.mark.anyio
async def test_get_mission_found():
    mission_id = str(uuid.uuid4())
    mission = _make_mission(id=mission_id, status="ACTIVE")

    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=_as_record(mission))

    app.state.db = pool
    app.state.redis = AsyncMock()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/missions/{mission_id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == mission_id


@pytest.mark.anyio
async def test_get_mission_not_found():
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=None)

    app.state.db = pool
    app.state.redis = AsyncMock()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/missions/00000000-0000-0000-0000-000000000000")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# State-machine enforcement
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "from_status,to_status,expected_code",
    [
        ("PENDING", "ACTIVE", 200),  # valid
        ("ACTIVE", "SYNTHESIZING", 200),  # valid
        ("SYNTHESIZING", "COMPLETE", 200),  # valid
        ("ACTIVE", "FAILED", 200),  # valid (any → FAILED)
        # Invalid / backwards
        ("COMPLETE", "PENDING", 409),
        ("COMPLETE", "ACTIVE", 409),
        ("FAILED", "ACTIVE", 409),
        ("ACTIVE", "PENDING", 409),
    ],
)
async def test_patch_state_transitions(from_status, to_status, expected_code):
    mission_id = str(uuid.uuid4())
    current = _make_mission(id=mission_id, status=from_status)
    updated = _make_mission(id=mission_id, status=to_status)

    pool = AsyncMock()
    # get_mission then update_mission_status
    pool.fetchrow = AsyncMock(side_effect=[_as_record(current), _as_record(updated)])

    redis = AsyncMock()
    redis.publish = AsyncMock(return_value=1)

    app.state.db = pool
    app.state.redis = redis

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(f"/missions/{mission_id}", json={"status": to_status})

    assert resp.status_code == expected_code


@pytest.mark.anyio
async def test_patch_invalid_status_value():
    mission_id = str(uuid.uuid4())
    app.state.db = AsyncMock()
    app.state.redis = AsyncMock()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(f"/missions/{mission_id}", json={"status": "BOGUS"})

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Evidence CRUD
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ingest_evidence():
    """POST /evidence → 201, response has both timestamp and created_at."""
    mission_id = str(uuid.uuid4())
    evidence = _make_evidence(mission_id=mission_id)

    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=_as_record(evidence))

    redis = AsyncMock()
    redis.publish = AsyncMock(return_value=1)

    app.state.db = pool
    app.state.redis = redis

    payload = {
        "mission_id": mission_id,
        "agent_id": "agent_0",
        "claim": "Test claim",
        "summary": "Test summary",
        "source_url": "https://example.com",
        "snippet": "Test snippet",
    }

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/evidence", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    # Both timestamp and created_at must be present (Bug 2 fix)
    assert "timestamp" in data
    assert "created_at" in data
    assert data["created_at"] == data["timestamp"]  # alias equality


@pytest.mark.anyio
async def test_evidence_found_redis_payload_has_created_at():
    """EVIDENCE_FOUND published to Redis must include created_at alias."""
    mission_id = str(uuid.uuid4())
    evidence = _make_evidence(mission_id=mission_id)

    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=_as_record(evidence))

    published_messages: list[str] = []

    async def capture_publish(channel, message):
        published_messages.append(message)
        return 1

    redis = AsyncMock()
    redis.publish = AsyncMock(side_effect=capture_publish)

    app.state.db = pool
    app.state.redis = redis

    payload = {
        "mission_id": mission_id,
        "agent_id": "agent_0",
        "claim": "Test claim",
        "summary": "Test summary",
        "source_url": "https://example.com",
        "snippet": "Test snippet",
    }

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/evidence", json=payload)

    assert published_messages, "Expected at least one Redis publish"
    msg = json.loads(published_messages[0])
    assert msg["type"] == "EVIDENCE_FOUND"
    event_payload = msg["payload"]
    # Bug 2: created_at must be present in the published payload
    assert (
        "created_at" in event_payload
    ), "EVIDENCE_FOUND payload missing created_at alias"
    assert event_payload["created_at"] == event_payload["timestamp"]


@pytest.mark.anyio
async def test_ingest_evidence_fk_violation():
    """POST /evidence with bad mission_id → 422."""
    import asyncpg

    pool = AsyncMock()
    pool.fetchrow = AsyncMock(
        side_effect=asyncpg.ForeignKeyViolationError("fk violation")
    )

    app.state.db = pool
    app.state.redis = AsyncMock()

    payload = {
        "mission_id": "00000000-0000-0000-0000-000000000000",
        "agent_id": "agent_0",
        "claim": "Test",
        "summary": "Test",
        "source_url": "https://example.com",
        "snippet": "Test",
    }

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/evidence", json=payload)

    assert resp.status_code == 422
    assert "mission" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_list_evidence():
    mission_id = str(uuid.uuid4())
    rows = [_make_evidence(mission_id=mission_id) for _ in range(3)]

    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=[_as_record(r) for r in rows])

    app.state.db = pool
    app.state.redis = AsyncMock()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/missions/{mission_id}/evidence")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    for item in data:
        assert "created_at" in item  # alias must be in REST response too


@pytest.mark.anyio
async def test_list_evidence_with_theme_filter():
    mission_id = str(uuid.uuid4())
    rows = [_make_evidence(mission_id=mission_id, theme="AI Investments")]

    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=[_as_record(r) for r in rows])

    app.state.db = pool
    app.state.redis = AsyncMock()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/missions/{mission_id}/evidence", params={"theme": "AI Investments"}
        )

    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# WS relay — connection and keepalive
# ---------------------------------------------------------------------------


def test_ws_relay_connection_accepted():
    """WS relay accepts a connection and sends a PING keepalive within 30s.

    Uses TestClient with a mock lifespan so no real DB/Redis is used (CI has no
    Postgres). Fake Redis pub/sub yields one event then blocks until disconnect.
    """
    import threading
    from contextlib import asynccontextmanager

    mission_id = str(uuid.uuid4())
    stop_event = threading.Event()

    test_event = json.dumps(
        {"type": "EVIDENCE_FOUND", "payload": {"claim": "hello"}, "ts": 0}
    )

    class FakePubSub:
        async def subscribe(self, ch):
            pass

        async def unsubscribe(self, ch):
            pass

        async def aclose(self):
            pass

        async def listen(self):
            yield {"type": "message", "data": test_event.encode()}
            while not stop_event.is_set():
                await asyncio.sleep(0.05)

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

    @asynccontextmanager
    async def mock_lifespan(app):
        app.state.db = AsyncMock()
        app.state.redis = FakeRedis()
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = mock_lifespan
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/mission/{mission_id}") as ws:
                msg = ws.receive_text()
                parsed = json.loads(msg)
                assert parsed.get("type") in ("EVIDENCE_FOUND", "PING")
                if parsed.get("type") == "EVIDENCE_FOUND":
                    assert parsed["payload"]["claim"] == "hello"
                stop_event.set()
    finally:
        app.router.lifespan_context = original_lifespan


@pytest.mark.anyio
async def test_ws_relay_channel_name():
    """events_channel() returns the correct Redis channel string."""
    from streaming.channels import events_channel

    assert events_channel("abc-123") == "mission:abc-123:events"


# ---------------------------------------------------------------------------
# SonicSession.trigger_response
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_sonic_session_trigger_response():
    """SonicSession.trigger_response() sends response.create to the WebSocket."""
    from models.sonic_client import SonicSession

    ws = AsyncMock()
    ws.send = AsyncMock()

    session = SonicSession(ws=ws, session_id="test-session")
    await session.trigger_response()

    ws.send.assert_called_once()
    sent = json.loads(ws.send.call_args[0][0])
    assert sent == {"type": "response.create"}
