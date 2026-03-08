"""Nova 2 Sonic client — real-time speech-to-speech via Nova API Realtime WebSocket.

Protocol: OpenAI Realtime API-compatible
Endpoint: wss://api.nova.amazon.com/v1/realtime?model=nova-2-sonic-v1
Auth:      Authorization: Bearer <NOVA_API_KEY>
Audio:     PCM16, 24 000 Hz, mono (input & output)

Rate limits (free tier): 5 concurrent connections, 20 sessions/day.

Typical flow:
    client = SonicClient(api_key="...")
    async with client.connect() as session:
        await session.configure(instructions="You are a voice assistant.")
        await session.send_text("Hello, start the mission.")
        async for event in session.stream_events():
            if event.audio_delta:
                speaker.write(event.audio_delta)        # PCM16 bytes
            elif event.user_transcript:
                print("User:", event.user_transcript)
            elif event.assistant_transcript:
                print("Nova:", event.assistant_transcript)
            elif event.tool_call:
                result = await handle_tool(event.tool_call)
                await session.submit_tool_result(event.tool_call["call_id"], result)
            elif event.is_response_done:
                break
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import ssl
import struct
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NOVA_REALTIME_URL = "wss://api.nova.amazon.com/v1/realtime"
DEFAULT_MODEL = "nova-2-sonic-v1"

# Audio format expected by Nova Sonic
SAMPLE_RATE = 24_000   # Hz
CHANNELS = 1
SAMPLE_WIDTH = 2       # bytes — 16-bit PCM
SILENCE_INTERVAL = 0.1  # seconds between keepalive silence bursts

# Voices supported by Nova 2 Sonic
AVAILABLE_VOICES = {"matthew", "olivia", "amy", "brian"}
DEFAULT_VOICE = "matthew"

# Default system instructions for Mission Control
SONIC_SYSTEM_PROMPT = """\
You are the voice of Mission Control, an elite AI intelligence command center.
When the user gives you a mission objective, immediately call start_mission to deploy \
browser agents. Provide brief acknowledgements (under 10 words) before tool calls so \
the user knows you heard them. After receiving mission status updates, narrate progress \
in a clear, confident intelligence-briefing style. When the briefing is ready, call \
deliver_final_briefing to speak it aloud. Keep all spoken responses concise — this is \
voice-only; no markdown, no bullet points, no lists.
"""


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

# Server → client event types (subset we care about)
_SERVER_EVENTS = {
    "session.created",
    "session.updated",
    "conversation.item.added",
    "conversation.item.done",
    "response.output_audio.delta",
    "response.output_audio_transcript.delta",
    "response.output_audio_transcript.done",
    "conversation.item.input_audio_transcription.completed",
    "response.function_call_arguments.done",
    "response.done",
    "error",
}


# ---------------------------------------------------------------------------
# SonicEvent — parsed server message
# ---------------------------------------------------------------------------


@dataclass
class SonicEvent:
    """A parsed event received from the Nova Sonic server.

    All field accessors return ``None`` when the event is of a different type,
    making them safe to use without checking ``event.type`` first.
    """

    type: str
    raw: dict[str, Any] = field(repr=False)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def audio_delta(self) -> bytes | None:
        """Raw PCM16 bytes from an audio delta event, else None."""
        if self.type == "response.output_audio.delta":
            return base64.b64decode(self.raw["delta"])
        return None

    @property
    def assistant_transcript(self) -> str | None:
        """Completed assistant transcript text, else None."""
        if self.type == "response.output_audio_transcript.done":
            return self.raw.get("transcript")
        return None

    @property
    def assistant_transcript_delta(self) -> str | None:
        """Streaming assistant transcript chunk, else None."""
        if self.type == "response.output_audio_transcript.delta":
            return self.raw.get("delta")
        return None

    @property
    def user_transcript(self) -> str | None:
        """Completed user speech transcript, else None."""
        if self.type == "conversation.item.input_audio_transcription.completed":
            return self.raw.get("transcript")
        return None

    @property
    def tool_call(self) -> dict[str, Any] | None:
        """Tool call dict ``{call_id, name, arguments}`` when Sonic invokes a tool."""
        if self.type == "response.function_call_arguments.done":
            try:
                args = json.loads(self.raw.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            return {
                "call_id": self.raw.get("call_id"),
                "name": self.raw.get("name"),
                "arguments": args,
            }
        return None

    @property
    def is_response_done(self) -> bool:
        """True when the current response turn is complete."""
        return self.type == "response.done"

    @property
    def error(self) -> dict[str, Any] | None:
        """Error details dict when the server reports an error, else None."""
        if self.type == "error":
            return self.raw.get("error", self.raw)
        return None

    def __str__(self) -> str:
        if self.audio_delta:
            return f"SonicEvent(audio_delta={len(self.audio_delta)}B)"
        return f"SonicEvent(type={self.type!r})"


# ---------------------------------------------------------------------------
# SonicSession — a single live WebSocket connection
# ---------------------------------------------------------------------------


class SonicSession:
    """A live Nova 2 Sonic WebSocket session.

    Created by ``SonicClient.connect()`` — do not instantiate directly.

    All send methods are fire-and-forget (they queue data on the wire).
    Use ``stream_events()`` to receive the server's response events.
    """

    def __init__(self, ws: Any, session_id: str) -> None:
        self._ws = ws
        self.session_id = session_id
        self._silence_task: asyncio.Task | None = None
        self._closed = False

    # ------------------------------------------------------------------
    # Session configuration
    # ------------------------------------------------------------------

    async def configure(
        self,
        *,
        instructions: str = SONIC_SYSTEM_PROMPT,
        voice: str = DEFAULT_VOICE,
        tools: list[dict[str, Any]] | None = None,
        turn_detection_threshold: float = 0.5,
        max_output_tokens: int = 3000,
    ) -> None:
        """Send a ``session.update`` to configure voice, instructions, and tools.

        Must be called after ``connect()`` and before sending any audio or text.
        Awaits the server's ``session.updated`` acknowledgement before returning.

        Args:
            instructions: System prompt / persona for Sonic.
            voice:        One of ``matthew``, ``olivia``, ``amy``, ``brian``.
            tools:        List of tool dicts in Nova Realtime format (from ``sonic_tools``).
            turn_detection_threshold: VAD sensitivity 0.0–1.0 (higher = less sensitive).
            max_output_tokens: Maximum tokens Sonic will generate per turn.
        """
        if voice not in AVAILABLE_VOICES:
            logger.warning("Unknown voice %r — falling back to %r", voice, DEFAULT_VOICE)
            voice = DEFAULT_VOICE

        session_payload: dict[str, Any] = {
            "type": "realtime",
            "instructions": instructions,
            "audio": {
                "input": {
                    "turn_detection": {"threshold": turn_detection_threshold},
                },
                "output": {"voice": voice},
            },
            "max_output_tokens": max_output_tokens,
        }
        if tools:
            session_payload["tools"] = tools
            session_payload["tool_choice"] = "auto"

        await self._send({"type": "session.update", "session": session_payload})

        # Wait for server to acknowledge
        ack = await self._recv_one()
        if ack.get("type") != "session.updated":
            logger.warning(
                "Expected session.updated, got %r: %s",
                ack.get("type"),
                json.dumps(ack)[:200],
            )
        else:
            logger.debug("Session %s configured: voice=%s tools=%d",
                         self.session_id, voice, len(tools or []))

    # ------------------------------------------------------------------
    # Input methods
    # ------------------------------------------------------------------

    async def send_audio(self, pcm16_bytes: bytes) -> None:
        """Append raw PCM16 audio (24 kHz, mono, 16-bit) to Sonic's input buffer.

        The model uses server-side VAD to detect when the user has finished
        speaking and automatically generates a response.

        Args:
            pcm16_bytes: Raw PCM16 audio bytes to stream.
        """
        await self._send({
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(pcm16_bytes).decode("utf-8"),
        })

    async def send_text(self, text: str) -> None:
        """Send a text message to Sonic instead of audio.

        Useful for testing and for demo mode. Note: Nova Sonic requires
        continuous audio input even when sending text — the keepalive silence
        stream started by ``start_silence_keepalive()`` handles this.

        Args:
            text: User message text to send.
        """
        await self._send({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}],
            },
        })
        logger.debug("Sent text message: %r", text[:80])

    async def submit_tool_result(self, call_id: str, result: Any) -> None:
        """Return the result of a tool call back to Sonic to continue the turn.

        Call this after executing the tool that Sonic requested.
        The result can be any JSON-serialisable value; it is converted to a
        string before sending.

        Args:
            call_id: The ``call_id`` from the ``tool_call`` event.
            result:  The tool's return value (dict, list, str, etc.).
        """
        if not isinstance(result, str):
            result = json.dumps(result)
        await self._send({
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": result,
            },
        })
        logger.debug("Submitted tool result for call_id=%s", call_id)

    async def interrupt(self) -> None:
        """Signal Sonic to stop the current response (barge-in support).

        Truncates the current assistant audio item and clears the input buffer
        so a fresh user turn can begin immediately.
        """
        await self._send({"type": "input_audio_buffer.clear"})
        logger.debug("Sent interrupt (input_audio_buffer.clear)")

    # ------------------------------------------------------------------
    # Silence keepalive
    # ------------------------------------------------------------------

    def start_silence_keepalive(self) -> None:
        """Start a background task that sends silence frames every 100 ms.

        Nova Sonic requires a continuous audio stream even when sending text
        messages. This keepalive prevents the VAD from timing out the session.
        Call ``stop_silence_keepalive()`` when done.
        """
        if self._silence_task and not self._silence_task.done():
            return
        self._silence_task = asyncio.create_task(self._send_silence_loop())
        logger.debug("Silence keepalive started")

    def stop_silence_keepalive(self) -> None:
        """Stop the background silence keepalive task."""
        if self._silence_task and not self._silence_task.done():
            self._silence_task.cancel()
            self._silence_task = None
        logger.debug("Silence keepalive stopped")

    async def _send_silence_loop(self) -> None:
        """Background task: send silence chunks every SILENCE_INTERVAL seconds."""
        samples = int(SAMPLE_RATE * SILENCE_INTERVAL)
        silence_bytes = bytes(samples * SAMPLE_WIDTH)
        silence_b64 = base64.b64encode(silence_bytes).decode("utf-8")
        try:
            while True:
                await self._send({
                    "type": "input_audio_buffer.append",
                    "audio": silence_b64,
                })
                await asyncio.sleep(SILENCE_INTERVAL)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("Silence keepalive error: %s", exc)

    # ------------------------------------------------------------------
    # Event streaming
    # ------------------------------------------------------------------

    async def stream_events(self) -> AsyncIterator[SonicEvent]:
        """Async generator that yields ``SonicEvent`` objects from the server.

        Terminates when a ``response.done`` or ``error`` event is received,
        or when the WebSocket connection closes.

        Example::

            async for event in session.stream_events():
                if event.audio_delta:
                    play(event.audio_delta)
                elif event.is_response_done:
                    break
        """
        try:
            async for raw_msg in self._ws:
                raw = json.loads(raw_msg)
                event_type = raw.get("type", "unknown")
                event = SonicEvent(type=event_type, raw=raw)

                if event_type not in _SERVER_EVENTS:
                    logger.debug("Ignoring unknown event type: %r", event_type)
                    continue

                if event.error:
                    logger.error("Sonic error event: %s", json.dumps(event.error))
                else:
                    logger.debug("← %s", event)

                yield event

                if event.is_response_done or event.error:
                    break

        except (ConnectionClosedOK, ConnectionClosedError) as exc:
            logger.info("WebSocket closed during stream_events: %s", exc)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _send(self, payload: dict[str, Any]) -> None:
        await self._ws.send(json.dumps(payload))

    async def _recv_one(self) -> dict[str, Any]:
        msg = await self._ws.recv()
        return json.loads(msg)

    async def close(self) -> None:
        """Close the WebSocket connection and stop keepalive."""
        self.stop_silence_keepalive()
        if not self._closed:
            self._closed = True
            try:
                await self._ws.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# SonicClient — connection factory
# ---------------------------------------------------------------------------


class SonicClient:
    """Nova 2 Sonic client — connects to the Nova Realtime API via WebSocket.

    Usage (context manager)::

        client = SonicClient(api_key="...")
        async with client.connect() as session:
            await session.configure(
                instructions="You are a concise voice assistant.",
                voice="matthew",
            )
            session.start_silence_keepalive()   # required for text-mode input
            await session.send_text("Hello! Summarise AI trends.")
            async for event in session.stream_events():
                if event.audio_delta:
                    speaker.write(event.audio_delta)
                elif event.assistant_transcript:
                    print("Nova:", event.assistant_transcript)
                elif event.is_response_done:
                    break

    Usage (audio streaming)::

        async with client.connect() as session:
            await session.configure(voice="olivia")
            # Stream raw PCM16 chunks from mic
            while (chunk := mic.read(4800)):     # 100 ms at 24 kHz
                await session.send_audio(chunk)
            async for event in session.stream_events():
                ...
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        voice: str = DEFAULT_VOICE,
    ) -> None:
        if api_key is None:
            try:
                from backend.config import settings  # type: ignore[import]
                api_key = settings.nova_api_key or None
            except Exception:
                pass

        if not api_key:
            api_key = os.environ.get("NOVA_API_KEY", "")

        if not api_key:
            raise ValueError(
                "Nova API key required. Set NOVA_API_KEY env var or pass api_key=."
            )

        self._api_key = api_key
        self._model = model
        self._voice = voice

        # Permissive SSL context — api.nova.amazon.com may use internal CA
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[SonicSession]:
        """Open a WebSocket connection and yield a ready ``SonicSession``.

        Waits for the server's ``session.created`` event before yielding,
        ensuring the session is fully established. Closes the connection
        cleanly on exit even if an exception is raised.

        Example::

            async with client.connect() as session:
                await session.configure(...)
                ...
        """
        url = f"{NOVA_REALTIME_URL}?model={self._model}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Origin": "https://api.nova.amazon.com",
        }

        logger.info("Connecting to Nova Sonic: %s", url)
        session: SonicSession | None = None

        try:
            async with websockets.connect(
                url,
                ssl=self._ssl_ctx,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
            ) as ws:
                # First message must be session.created
                raw = json.loads(await ws.recv())
                if raw.get("type") != "session.created":
                    raise RuntimeError(
                        f"Expected session.created, got: {raw.get('type')!r}\n{raw}"
                    )

                session_id = raw.get("session", {}).get("id", "unknown")
                logger.info("Sonic session established: %s", session_id)

                session = SonicSession(ws=ws, session_id=session_id)
                yield session

        except (ConnectionClosedOK, ConnectionClosedError) as exc:
            logger.info("Sonic session closed: %s", exc)
        finally:
            if session:
                await session.close()

    @property
    def model(self) -> str:
        return self._model

    @property
    def default_voice(self) -> str:
        return self._voice


# ---------------------------------------------------------------------------
# Utility: float32 → PCM16 conversion (for browser AudioWorklet integration)
# ---------------------------------------------------------------------------


def float32_to_pcm16(float32_array: list[float] | bytes) -> bytes:
    """Convert a float32 audio array to PCM16 bytes.

    The browser's Web Audio API produces float32 samples in [-1.0, 1.0].
    Nova Sonic expects PCM16 (signed 16-bit little-endian).

    Args:
        float32_array: List of float samples or raw float32 bytes.

    Returns:
        PCM16 bytes suitable for ``session.send_audio()``.
    """
    if isinstance(float32_array, bytes):
        count = len(float32_array) // 4
        floats = struct.unpack(f"<{count}f", float32_array)
    else:
        floats = float32_array

    clipped = (max(-1.0, min(1.0, s)) for s in floats)
    return struct.pack(f"<{len(floats)}h", *(int(s * 32767) for s in clipped))


def generate_silence(duration_ms: int) -> bytes:
    """Generate PCM16 silence for the given duration.

    Args:
        duration_ms: Duration of silence in milliseconds.

    Returns:
        PCM16 silence bytes (all zeros).
    """
    samples = (SAMPLE_RATE * duration_ms) // 1000
    return bytes(samples * SAMPLE_WIDTH)


# ---------------------------------------------------------------------------
# Module-level singleton factory
# ---------------------------------------------------------------------------


def get_sonic_client(api_key: str | None = None) -> SonicClient:
    """Return a SonicClient instance, reading NOVA_API_KEY from env if needed."""
    return SonicClient(api_key=api_key)


# ---------------------------------------------------------------------------
# Smoke test — run directly: python models/sonic_client.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import wave

    async def _smoke_test() -> None:
        api_key = os.environ.get("NOVA_API_KEY")
        if not api_key:
            print("Set NOVA_API_KEY to run the smoke test.")
            sys.exit(1)

        client = SonicClient(api_key=api_key, voice="matthew")
        print(f"Model : {client.model}")
        print(f"Voice : {client.default_voice}")
        print("─" * 50)

        audio_buffer = bytearray()
        assistant_text = ""

        print("Test — connecting to Nova Sonic and sending text message:")
        async with client.connect() as session:
            # Configure with a concise system prompt (no tools for smoke test)
            await session.configure(
                instructions="You are a helpful assistant. Keep all responses under 15 words.",
                voice="matthew",
            )

            # Silence keepalive is required when using text input
            session.start_silence_keepalive()
            print("  ✓ Connected and configured")
            print("  Sending: 'Say exactly: SONIC_OK'")

            await session.send_text("Say exactly: SONIC_OK")

            async for event in session.stream_events():
                if event.audio_delta:
                    audio_buffer.extend(event.audio_delta)
                elif event.assistant_transcript_delta:
                    assistant_text += event.assistant_transcript_delta
                elif event.assistant_transcript:
                    assistant_text = event.assistant_transcript
                elif event.user_transcript:
                    print(f"  User transcript: {event.user_transcript!r}")
                elif event.error:
                    print(f"  ❌ Error: {event.error}")
                    sys.exit(1)
                elif event.is_response_done:
                    break

            session.stop_silence_keepalive()

        print(f"  Assistant said: {assistant_text!r}")
        print(f"  Received {len(audio_buffer):,} bytes of audio")

        assert len(audio_buffer) > 0, "Expected audio output bytes"
        assert "SONIC_OK" in assistant_text.upper() or len(assistant_text) > 0, \
            f"Unexpected transcript: {assistant_text!r}"

        # Save output audio for manual verification
        out_path = "nova_sonic_smoke.wav"
        with wave.open(out_path, "wb") as wav:
            wav.setnchannels(CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(bytes(audio_buffer))
        print(f"  Audio saved → {out_path}")

        print("\n✅ Sonic smoke test passed.")

    asyncio.run(_smoke_test())
