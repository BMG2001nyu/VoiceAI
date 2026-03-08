"""WebSocket relay — forwards Redis pub/sub events to browser clients.

GET /ws/mission/{mission_id}

On connect:
  - Subscribe to Redis mission:{id}:events
  - Forward every message to the browser as text (JSON string)

On browser disconnect:
  - Cancel the relay task, unsubscribe, close the pubsub connection
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from streaming.channels import events_channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streaming"])


async def _relay_loop(pubsub, websocket: WebSocket) -> None:
    """Continuously forward Redis messages to the WebSocket client."""
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                await websocket.send_text(data)
            except Exception:
                # Client has disconnected — stop the relay.
                return


@router.websocket("/ws/mission/{mission_id}")
async def ws_mission_relay(websocket: WebSocket, mission_id: str) -> None:
    await websocket.accept()
    redis = websocket.app.state.redis
    pubsub = redis.pubsub()
    channel = events_channel(mission_id)
    await pubsub.subscribe(channel)
    logger.info("WS relay connected for mission %s", mission_id)

    relay_task = asyncio.create_task(_relay_loop(pubsub, websocket))

    try:
        # Block here until the browser closes the connection.
        # receive_bytes() is used because the client never sends to this socket;
        # it raises WebSocketDisconnect when the connection drops.
        while True:
            try:
                await asyncio.wait_for(websocket.receive_bytes(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send a keepalive ping so load balancers don't close idle connections.
                try:
                    await websocket.send_text('{"type":"PING"}')
                except Exception:
                    break
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        relay_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await relay_task
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        logger.info("WS relay disconnected for mission %s", mission_id)
