"""Voice Gateway — bidirectional WebSocket bridge between the browser and Nova Sonic.

GET /ws/voice

Flow:
  1. Accept browser WebSocket connection
  2. Open a SonicClient session (Nova 2 Sonic via Nova API)
  3. Configure session with SONIC_SYSTEM_PROMPT + SONIC_TOOLS
  4. Run two concurrent tasks:
       browser_to_sonic — forward raw PCM audio bytes from browser to Sonic
       sonic_to_browser — forward Sonic events (audio, transcripts, tool calls) to browser
  5. Tool call handlers call repository functions directly (no internal HTTP):
       start_mission           → missions.repository.create_mission + plan_tasks
       get_mission_status      → missions.repository.get_mission
       get_new_findings        → evidence.repository.list_evidence
       ask_user_for_clarification → no-op (Sonic speaks the question; return ack)
       deliver_final_briefing  → missions.repository.set_briefing + publish STATUS_CHANGE
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings
from missions import repository as missions_repo
from evidence import repository as evidence_repo
from streaming.channels import publish, publish_timeline_event

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])

# ── System prompt (imported from sonic_client where it lives) ─────────────────

try:
    from models.sonic_client import SONIC_SYSTEM_PROMPT
except ImportError:
    SONIC_SYSTEM_PROMPT = (
        "You are the voice of Mission Control. When the user gives you a mission "
        "objective, immediately call start_mission. Keep spoken responses concise."
    )

try:
    from models.sonic_tools import SONIC_TOOLS
except ImportError:
    SONIC_TOOLS = []


# ── Tool handlers ─────────────────────────────────────────────────────────────


async def _handle_tool(
    tool_call: dict[str, Any],
    app_state: Any,
    session_state: dict,
) -> dict[str, Any]:
    """Dispatch a Sonic tool call to the appropriate repository function."""
    name = tool_call.get("name", "")
    args = tool_call.get("arguments", {})
    db = app_state.db
    redis = app_state.redis

    if name == "start_mission":
        objective = args.get("objective", "")
        if not objective:
            return {"error": "objective is required"}

        # Create mission row + call Nova Lite for task graph.
        mission = await missions_repo.create_mission(db, objective)
        mission_id = mission["id"]
        session_state["mission_id"] = mission_id

        try:
            from models.lite_client import LiteClient

            client = LiteClient(api_key=settings.nova_api_key)
            task_graph = await client.plan_tasks(objective)
        except Exception as exc:
            logger.error("plan_tasks failed: %s", exc)
            task_graph = []

        mission = await missions_repo.set_task_graph(db, mission_id, task_graph)

        # Serialise datetimes before publishing.
        mission_payload = dict(mission)
        for key in ("created_at", "updated_at"):
            if hasattr(mission_payload.get(key), "isoformat"):
                mission_payload[key] = mission_payload[key].isoformat()

        await publish(redis, mission_id, "MISSION_STATUS", mission_payload)
        await publish_timeline_event(
            redis,
            mission_id,
            {
                "id": str(uuid.uuid4()),
                "type": "agent_assigned",
                "description": f"Mission started: {objective[:80]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return {
            "mission_id": mission_id,
            "status": "ACTIVE",
            "task_count": len(task_graph),
            "message": f"Mission deployed with {len(task_graph)} research tasks.",
        }

    elif name == "get_mission_status":
        mission_id = args.get("mission_id") or session_state.get("mission_id")
        if not mission_id:
            return {"error": "mission_id is required"}
        mission = await missions_repo.get_mission(db, mission_id)
        if mission is None:
            return {"error": f"Mission {mission_id} not found"}
        evidence_rows = await evidence_repo.list_evidence(db, mission_id, limit=200)
        return {
            "mission_id": mission_id,
            "status": mission["status"],
            "evidence_count": len(evidence_rows),
            "task_count": len(mission.get("task_graph") or []),
        }

    elif name == "get_new_findings":
        mission_id = args.get("mission_id") or session_state.get("mission_id")
        if not mission_id:
            return {"error": "mission_id is required"}
        limit = min(int(args.get("limit", 5)), 20)
        rows = await evidence_repo.list_evidence(db, mission_id, limit=limit)
        findings = [
            {
                "claim": r["claim"],
                "summary": r["summary"],
                "source_url": r["source_url"],
                "confidence": r["confidence"],
                "theme": r.get("theme"),
            }
            for r in rows
        ]
        return {"findings": findings, "count": len(findings)}

    elif name == "ask_user_for_clarification":
        # Sonic will speak the question; no backend action needed.
        return {"acknowledged": True, "question": args.get("question", "")}

    elif name == "deliver_final_briefing":
        mission_id = args.get("mission_id") or session_state.get("mission_id")
        briefing_text = args.get("briefing_text", "")
        if not mission_id:
            return {"error": "mission_id is required"}

        await missions_repo.set_briefing(db, mission_id, briefing_text)

        mission_payload = {"mission_id": mission_id, "status": "COMPLETE"}
        await publish(redis, mission_id, "MISSION_STATUS", mission_payload)
        await publish_timeline_event(
            redis,
            mission_id,
            {
                "id": str(uuid.uuid4()),
                "type": "mission_complete",
                "description": "Final intelligence briefing delivered",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return {"delivered": True, "mission_id": mission_id}

    else:
        logger.warning("Unknown tool call: %s", name)
        return {"error": f"Unknown tool: {name}"}


# ── WebSocket endpoint ────────────────────────────────────────────────────────


@router.websocket("/ws/voice")
async def ws_voice(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("Voice gateway: client connected")

    if not settings.nova_api_key:
        await websocket.send_json(
            {"type": "ERROR", "message": "NOVA_API_KEY not configured"}
        )
        await websocket.close()
        return

    from models.sonic_client import SonicClient

    session_state: dict[str, Any] = {"mission_id": None}
    app_state = websocket.app.state
    redis = app_state.redis

    client = SonicClient(api_key=settings.nova_api_key)

    async def browser_to_sonic(session) -> None:
        """Forward browser audio/control messages to Nova Sonic.

        Handles two frame types:
          - bytes  → raw PCM16 audio, forwarded to Sonic as audio input
          - text   → JSON control message; currently supports {"type":"interrupt"}
        """
        try:
            while True:
                # receive() handles both bytes and text frames without raising on mismatch.
                msg = await websocket.receive()

                if msg["type"] == "websocket.disconnect":
                    break

                raw_bytes = msg.get("bytes")
                raw_text = msg.get("text")

                if raw_bytes:
                    await session.send_audio(raw_bytes)
                elif raw_text:
                    try:
                        ctrl = json.loads(raw_text)
                        if ctrl.get("type") == "interrupt":
                            await session.interrupt()
                            logger.info("Voice gateway: barge-in interrupt received")
                    except (json.JSONDecodeError, Exception) as exc:
                        logger.warning("browser_to_sonic: unhandled text frame: %s", exc)
        except (WebSocketDisconnect, Exception):
            pass

    async def sonic_to_browser(session) -> None:
        """Forward Nova Sonic events to the browser and handle tool calls.

        Runs in an outer loop so multi-turn conversations work correctly.
        Each call to stream_events() handles exactly one response turn;
        the outer loop restarts it for subsequent turns.
        """
        while True:
            turn_had_events = False
            async for event in session.stream_events():
                turn_had_events = True

                if event.error:
                    logger.error("Sonic error: %s", event.error)
                    with contextlib.suppress(Exception):
                        await websocket.send_json({"type": "ERROR", "detail": event.error})
                    return  # Fatal — exit the task on error

                elif event.audio_delta:
                    with contextlib.suppress(Exception):
                        await websocket.send_bytes(event.audio_delta)

                elif event.assistant_transcript:
                    ts = datetime.now(timezone.utc).isoformat()
                    transcript_payload = {
                        "id": str(uuid.uuid4()),
                        "role": "assistant",
                        "text": event.assistant_transcript,
                        "timestamp": ts,
                    }
                    with contextlib.suppress(Exception):
                        await websocket.send_json(
                            {"type": "VOICE_TRANSCRIPT", "payload": transcript_payload}
                        )
                    # Also publish to the mission's events channel if we have an ID.
                    mission_id = session_state.get("mission_id")
                    if mission_id:
                        with contextlib.suppress(Exception):
                            await publish(
                                redis, mission_id, "VOICE_TRANSCRIPT", transcript_payload
                            )

                elif event.user_transcript:
                    ts = datetime.now(timezone.utc).isoformat()
                    transcript_payload = {
                        "id": str(uuid.uuid4()),
                        "role": "user",
                        "text": event.user_transcript,
                        "timestamp": ts,
                    }
                    with contextlib.suppress(Exception):
                        await websocket.send_json(
                            {"type": "VOICE_TRANSCRIPT", "payload": transcript_payload}
                        )

                elif event.tool_call:
                    tool_name = event.tool_call.get("name", "unknown")
                    logger.info("Sonic tool call: %s", tool_name)
                    try:
                        result = await _handle_tool(
                            event.tool_call, app_state, session_state
                        )
                    except Exception as exc:
                        logger.error("Tool handler error (%s): %s", tool_name, exc)
                        result = {"error": str(exc)}
                    with contextlib.suppress(Exception):
                        await session.submit_tool_result(event.tool_call["call_id"], result)
                        # Explicitly trigger Sonic's next response after tool result.
                        # The Nova Realtime API does not auto-generate after function_call_output.
                        await session.trigger_response()

            # stream_events() exited (response.done or connection closed).
            # If no events at all, the connection is closed — stop looping.
            if not turn_had_events:
                return

    try:
        async with client.connect() as session:
            await session.configure(
                instructions=SONIC_SYSTEM_PROMPT,
                tools=SONIC_TOOLS,
            )
            session.start_silence_keepalive()

            browser_task = asyncio.create_task(browser_to_sonic(session))
            sonic_task = asyncio.create_task(sonic_to_browser(session))

            done, pending = await asyncio.wait(
                {browser_task, sonic_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.gather(*pending, return_exceptions=True)

    except (WebSocketDisconnect, Exception) as exc:
        logger.info("Voice gateway: session ended (%s: %s)", type(exc).__name__, exc)
    finally:
        logger.info("Voice gateway: client disconnected")
