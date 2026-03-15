# Voice Audio Format Specification

## Overview

Mission Control uses a bidirectional audio pipeline between the browser and Amazon Nova 2 Sonic. This document specifies the audio formats at each stage.

## Browser → Backend (Microphone Input)

| Parameter | Value |
|-----------|-------|
| Format | PCM16 (signed 16-bit little-endian) |
| Sample Rate | 16,000 Hz (16 kHz) |
| Channels | 1 (mono) |
| Bit Depth | 16 bits |
| Byte Rate | 32,000 bytes/sec |
| Frame Size | 640 bytes (20 ms at 16 kHz) |

### Browser Implementation

Use `AudioWorkletProcessor` for raw PCM extraction:

```javascript
// In your AudioWorklet processor
class PCMProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0][0]; // mono channel, float32
    // Convert float32 [-1.0, 1.0] to int16
    const pcm16 = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      pcm16[i] = Math.max(-32768, Math.min(32767, input[i] * 32767));
    }
    this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    return true;
  }
}
```

Configure AudioContext at 16 kHz:
```javascript
const ctx = new AudioContext({ sampleRate: 16000 });
```

Send PCM chunks via WebSocket as binary frames:
```javascript
ws.send(pcm16Buffer); // ArrayBuffer of PCM16 bytes
```

## Backend Processing (VAD — Optional)

When Voice Activity Detection is enabled (`backend/gateway/vad.py`):

- Frames: 20 ms (640 bytes at 16 kHz)
- Aggressiveness: Mode 3 (most aggressive filtering)
- Silence threshold: 300 ms (15 consecutive silent frames)
- Pre-speech buffer: 3 frames (60 ms) to avoid clipping

When VAD is disabled (default for demo), raw PCM is passed through directly.

## Backend → Nova Sonic (Upstream)

| Parameter | Value |
|-----------|-------|
| Format | PCM16 (signed 16-bit little-endian) |
| Sample Rate | 24,000 Hz (24 kHz) |
| Channels | 1 (mono) |
| Encoding | base64 (over WebSocket JSON) |

**Important:** Nova Sonic expects 24 kHz audio. If the browser sends 16 kHz, the backend must resample. Current implementation: browser audio is sent at the browser's native rate and Sonic handles resampling internally. For best quality, configure the browser AudioContext at 24 kHz:

```javascript
const ctx = new AudioContext({ sampleRate: 24000 });
// Frame size at 24 kHz: 960 bytes per 20 ms frame
```

## Nova Sonic → Browser (Speaker Output)

| Parameter | Value |
|-----------|-------|
| Format | PCM16 (signed 16-bit little-endian) |
| Sample Rate | 24,000 Hz (24 kHz) |
| Channels | 1 (mono) |
| Transport | Raw binary WebSocket frames |

### Browser Playback

```javascript
// Create AudioContext at 24 kHz for Sonic output
const playbackCtx = new AudioContext({ sampleRate: 24000 });

// Convert received PCM16 bytes to float32 for Web Audio API
function pcm16ToFloat32(pcm16Buffer) {
  const int16 = new Int16Array(pcm16Buffer);
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 32768.0;
  }
  return float32;
}
```

## Control Messages

JSON text frames on the same WebSocket:

| Message | Direction | Purpose |
|---------|-----------|---------|
| `{"type": "interrupt"}` | Browser → Backend | Barge-in: stop current Sonic response |
| `{"type": "VOICE_TRANSCRIPT", ...}` | Backend → Browser | Transcript event |
| `{"type": "ERROR", ...}` | Backend → Browser | Error notification |

## Barge-in / Interrupt Protocol

Barge-in allows the user to interrupt Nova Sonic mid-response by speaking or sending an explicit interrupt message.

### How It Works

1. The browser sends `{"type": "interrupt"}` as a JSON text frame on the voice WebSocket.
2. The backend's `browser_to_sonic` handler detects this message and calls `session.interrupt()`.
3. `SonicSession.interrupt()` sends `input_audio_buffer.clear` to Nova Sonic, which stops the current response generation.
4. The `sonic_to_browser` loop handles the response completion and the outer loop restarts for the next conversational turn.

### Implementation Notes

- The interrupt is immediate: Sonic stops generating audio within one frame.
- Any buffered audio already sent to the browser may still play; the browser should discard queued audio on interrupt.
- The backend tracks no additional state for barge-in; the existing stream event loop handles turn boundaries naturally.

## Silence Keepalive

Nova Sonic requires continuous audio input even during text-only interactions. The backend sends silence frames (all-zero PCM16) every 100 ms to keep the session alive. This is handled automatically by `SonicSession.start_silence_keepalive()`.

## Summary Diagram

```
Browser Mic (16/24 kHz PCM16)
    | binary WS frame
    v
[VAD filter] (optional)
    | base64 encoded
    v
Nova Sonic (24 kHz PCM16)
    | base64 decoded
    v
[PCM16 bytes]
    | binary WS frame
    v
Browser Speaker (24 kHz PCM16 -> float32 -> AudioContext)
```
