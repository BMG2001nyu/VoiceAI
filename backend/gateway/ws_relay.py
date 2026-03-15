import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import asyncio as aioredis
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_redis_client():
    return aioredis.from_url(settings.redis_url, decode_responses=True)


@router.websocket("/ws/v2/mission/{mission_id}")
async def mission_ws(websocket: WebSocket, mission_id: str):
    await websocket.accept()
    logger.info(f"WebSocket client connected for mission: {mission_id}")

    redis = await get_redis_client()
    pubsub = redis.pubsub()

    # Channels to subscribe to
    mission_channel = f"mission:{mission_id}:events"
    findings_pattern = "agent:*:findings"

    await pubsub.subscribe(mission_channel)
    await pubsub.psubscribe(findings_pattern)

    # Optional: Send initial MISSION_STATUS if we had a DB to query
    # For now, we wait for Redis events to drive the UI

    try:
        async for message in pubsub.listen():
            if message["type"] in ["message", "pmessage"]:
                data = message.get("data")
                if data:
                    await websocket.send_text(data)
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for mission: {mission_id}")
    except Exception as e:
        logger.error(f"Error in mission_ws: {e}")
    finally:
        await pubsub.unsubscribe(mission_channel)
        await pubsub.punsubscribe(findings_pattern)
        await redis.close()


@router.websocket("/ws/v2/voice")
async def voice_ws(websocket: WebSocket):
    """
    Placeholder for Voice Gateway relay.
    In production, this would relay to Bedrock/Realtime API.
    """
    await websocket.accept()
    logger.info("Voice WebSocket client connected")

    try:
        while True:
            # Handle incoming audio chunks or control messages
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "start":
                logger.info("Voice session started")
            elif msg.get("type") == "stop":
                logger.info("Voice session stopped")
                break
            elif msg.get("type") == "interrupt":
                logger.info("Voice interruption triggered")
                # Relay interrupt to TTS/LLM

    except WebSocketDisconnect:
        logger.info("Voice WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in voice_ws: {e}")
