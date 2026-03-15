# Frontend Streaming Architecture

## Overview

The War Room UI receives real-time events from the backend via WebSocket at `/ws/mission/{id}`. Events include agent status updates, evidence findings, timeline events, and voice transcripts.

## Event Flow

```
Backend Redis pub/sub
    ↓
/ws/mission/{id} (WebSocket relay)
    ↓
useWebSocket.ts (connection management)
    ↓
useThrottledDispatch (batching + rate limiting)
    ↓
Zustand store (reactive state)
    ↓
React components (auto-render on state change)
```

## Backpressure Strategy

### Problem
During active missions, the backend can emit 20+ events/second. Dispatching each event individually causes excessive React re-renders and potential UI jank.

### Solution: Batched Flush

Events are queued in `useThrottledStore.ts` and flushed every **150ms**:

1. **Immediate dispatch**: `MISSION_STATUS` events bypass the queue entirely (mission-critical, affects header display).
2. **Collapse duplicates**: Multiple `AGENT_UPDATE` events for the same `agent_id` within a flush window are collapsed — only the latest state is applied.
3. **Burst protection**: If the queue exceeds **100 events** in a single flush cycle, `EVIDENCE_FOUND` events are dropped for that cycle. `AGENT_UPDATE` and `MISSION_STATUS` are always processed.

### Event Priority

| Event Type | Priority | Burst Behavior |
|------------|----------|----------------|
| `MISSION_STATUS` | Critical | Always immediate |
| `AGENT_UPDATE` | High | Always processed (collapsed) |
| `TIMELINE_EVENT` | Medium | Processed normally |
| `VOICE_TRANSCRIPT` | Medium | Processed normally |
| `EVIDENCE_FOUND` | Normal | Dropped during burst |

### Performance Targets

- **60 fps** maintained under burst of 20 events/second
- **< 150ms** latency from WebSocket message to UI update (one flush interval)
- **No dropped** MISSION_STATUS or AGENT_UPDATE events

## Evidence Board

The Evidence Board (`EvidenceBoard.tsx`) uses native CSS `overflow-y-auto` scrolling. Evidence records are deduplicated by `id` in the Zustand store to prevent duplicates after WebSocket reconnection.

## Reconnection

On WebSocket disconnect, the hook automatically reconnects with exponential backoff (1s to 30s max with jitter). On reconnect, the store is rehydrated from the server's initial `MISSION_STATUS` message.
