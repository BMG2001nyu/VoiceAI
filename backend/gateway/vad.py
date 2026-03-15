"""Voice Activity Detection — optional audio chunking before Sonic.

Uses webrtcvad for lightweight silence detection. When enabled, only speech
frames are forwarded to Nova Sonic, reducing unnecessary API traffic.

Audio format: PCM16, 16 kHz, mono (from browser microphone).
Frame size: 20 ms = 640 bytes at 16 kHz 16-bit.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Generator

logger = logging.getLogger(__name__)

# Frame duration in ms — webrtcvad supports 10, 20, or 30 ms
FRAME_DURATION_MS = 20
# Sample rate expected from browser mic
BROWSER_SAMPLE_RATE = 16_000
SAMPLE_WIDTH = 2  # 16-bit PCM
FRAME_SIZE = (BROWSER_SAMPLE_RATE * FRAME_DURATION_MS // 1000) * SAMPLE_WIDTH  # 640 bytes

# Silence threshold: consecutive silent frames before declaring end-of-utterance
SILENCE_THRESHOLD_FRAMES = 15  # 300 ms at 20 ms/frame

# Pre-speech buffer: keep N frames before speech starts (avoids clipping leading consonants)
PRE_SPEECH_BUFFER = 3


class VoiceActivityDetector:
    """Stateful VAD that buffers audio and yields speech chunks.

    Usage:
        vad = VoiceActivityDetector(aggressiveness=3)
        for chunk in vad.process(raw_pcm_bytes):
            await session.send_audio(chunk)
    """

    def __init__(self, aggressiveness: int = 3) -> None:
        """Initialize the VAD.

        Args:
            aggressiveness: webrtcvad aggressiveness mode (0-3).
                           3 = most aggressive (filters most non-speech).
        """
        self._aggressiveness = aggressiveness
        self._vad = None  # Lazy init — webrtcvad may not be installed
        self._speech_buffer = bytearray()
        self._pre_buffer: deque[bytes] = deque(maxlen=PRE_SPEECH_BUFFER)
        self._silent_frame_count = 0
        self._in_speech = False
        self._initialized = False

    def _ensure_init(self) -> bool:
        """Lazily initialize webrtcvad. Returns False if not available."""
        if self._initialized:
            return self._vad is not None
        self._initialized = True
        try:
            import webrtcvad

            self._vad = webrtcvad.Vad(self._aggressiveness)
            logger.info("VAD initialized (aggressiveness=%d)", self._aggressiveness)
            return True
        except ImportError:
            logger.warning(
                "webrtcvad not installed — VAD disabled, passing audio through"
            )
            return False

    def process(self, pcm_bytes: bytes) -> Generator[bytes, None, None]:
        """Process raw PCM16 audio and yield speech segments.

        If webrtcvad is not installed, yields the input unchanged (passthrough).

        Args:
            pcm_bytes: Raw PCM16 audio bytes (16 kHz, mono).

        Yields:
            Speech audio chunks (may be larger than input due to buffering).
        """
        if not self._ensure_init():
            # Passthrough mode — no VAD filtering
            yield pcm_bytes
            return

        # Split into frames
        offset = 0
        while offset + FRAME_SIZE <= len(pcm_bytes):
            frame = pcm_bytes[offset : offset + FRAME_SIZE]
            offset += FRAME_SIZE

            is_speech = self._vad.is_speech(frame, BROWSER_SAMPLE_RATE)

            if is_speech:
                if not self._in_speech:
                    # Speech just started — flush pre-buffer
                    self._in_speech = True
                    self._silent_frame_count = 0
                    for pre_frame in self._pre_buffer:
                        self._speech_buffer.extend(pre_frame)
                    self._pre_buffer.clear()
                self._speech_buffer.extend(frame)
                self._silent_frame_count = 0
            else:
                if self._in_speech:
                    # Still in speech, counting silence
                    self._speech_buffer.extend(frame)
                    self._silent_frame_count += 1
                    if self._silent_frame_count >= SILENCE_THRESHOLD_FRAMES:
                        # End of utterance — yield buffered speech
                        yield bytes(self._speech_buffer)
                        self._speech_buffer.clear()
                        self._in_speech = False
                        self._silent_frame_count = 0
                else:
                    # Not in speech — add to pre-buffer
                    self._pre_buffer.append(frame)

    def flush(self) -> bytes | None:
        """Flush any remaining speech buffer (call on disconnect).

        Returns:
            Remaining speech bytes, or None if buffer is empty.
        """
        if self._speech_buffer:
            result = bytes(self._speech_buffer)
            self._speech_buffer.clear()
            self._in_speech = False
            self._silent_frame_count = 0
            return result
        return None

    def reset(self) -> None:
        """Reset VAD state for a new conversation turn."""
        self._speech_buffer.clear()
        self._pre_buffer.clear()
        self._silent_frame_count = 0
        self._in_speech = False
