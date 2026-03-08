# Mission Control — Redis Pub/Sub Event Reference

All real-time events flow through Redis pub/sub. Clients subscribe to a mission's
events channel and receive JSON messages in the envelope format below.

---

## Channel Names

| Channel | Pattern | Purpose |
|---------|---------|---------|
| `mission:{id}:events` | mission-scoped | All UI-facing events — agent updates, evidence, status, voice |
| `mission:{id}:agents` | mission-scoped | Agent heartbeats (health / liveness) |
| `mission:{id}:control` | mission-scoped | Orchestrator commands to agents (STOP, REDIRECT) |

---

## Message Envelope

Every message published to `mission:{id}:events` has this structure:

```json
{
  "type": "<EVENT_TYPE>",
  "payload": { ... },
  "ts": 1710000000.123
}
```

- `type` — one of the event types below
- `payload` — event-specific data (see schemas below)
- `ts` — Unix timestamp (float) of when the event was published

---

## Event Types

### `MISSION_STATUS`

Published when a mission is created or when `PATCH /missions/{id}` changes status.
The frontend replaces its full mission state with this payload.

```json
{
  "type": "MISSION_STATUS",
  "payload": {
    "id": "uuid",
    "objective": "Find Sequoia AI investments 2025",
    "status": "ACTIVE",
    "task_graph": [
      {
        "description": "Scrape sequoiacap.com for portfolio and partners",
        "agent_type": "OFFICIAL_SITE",
        "priority": 9,
        "dependencies": []
      }
    ],
    "created_at": "2026-03-08T12:00:00Z",
    "updated_at": "2026-03-08T12:00:05Z",
    "briefing": null
  },
  "ts": 1710000005.0
}
```

**Frontend handler:** `setMission(msg.payload)`

---

### `AGENT_UPDATE`

Published when an agent changes status (IDLE → ASSIGNED → BROWSING → REPORTING).

```json
{
  "type": "AGENT_UPDATE",
  "payload": {
    "agent_id": "agent_2",
    "status": "BROWSING",
    "task_type": "REDDIT_HN",
    "objective": "Find founder complaints about Sequoia on Reddit and HN",
    "site_url": "reddit.com"
  },
  "ts": 1710000010.0
}
```

**Frontend handler:** `updateAgent(msg.payload)`

---

### `EVIDENCE_FOUND`

Published by `POST /evidence` after a row is inserted. Causes a new evidence card
to appear in the War Room Evidence Board.

```json
{
  "type": "EVIDENCE_FOUND",
  "payload": {
    "id": "uuid",
    "mission_id": "uuid",
    "agent_id": "agent_0",
    "claim": "Sequoia has 8 active AI-focused partners as of 2025",
    "summary": "Sequoia's website lists 8 partners with explicit AI/ML expertise.",
    "source_url": "https://sequoiacap.com/people",
    "snippet": "Sonya Huang (AI), Pat Grady...",
    "confidence": 0.95,
    "novelty": 1.0,
    "theme": "Partner Priorities",
    "screenshot_s3_key": null,
    "timestamp": "2026-03-08T12:00:15Z"
  },
  "ts": 1710000015.0
}
```

**Frontend handler:** `addEvidence(msg.payload.evidence)` ← note: ws_relay forwards `payload` directly

---

### `TIMELINE_EVENT`

Published when a noteworthy system event occurs (agent assigned, evidence found, etc.).
These populate the Mission Timeline panel.

```json
{
  "type": "TIMELINE_EVENT",
  "payload": {
    "id": "uuid",
    "type": "evidence_found",
    "description": "agent_0 found evidence: Sequoia has 8 active AI-focused partners",
    "timestamp": "2026-03-08T12:00:15Z",
    "agent_id": "agent_0"
  },
  "ts": 1710000015.0
}
```

**Event type values:** `agent_assigned`, `evidence_found`, `agent_redirected`,
`agent_timeout`, `synthesis_start`, `mission_complete`, `contradiction_detected`

**Frontend handler:** `addTimelineEvent(msg.payload)`

---

### `VOICE_TRANSCRIPT`

Published by the Voice Gateway when Nova Sonic produces a completed transcript
(user speech or assistant response). Populates the VoicePanel transcript feed
and is also forwarded to the War Room via the mission events channel.

```json
{
  "type": "VOICE_TRANSCRIPT",
  "payload": {
    "id": "uuid",
    "role": "assistant",
    "text": "Deploying six agents now. I'll report back as findings come in.",
    "timestamp": "2026-03-08T12:00:02Z"
  },
  "ts": 1710000002.0
}
```

**`role` values:** `"user"` | `"assistant"`

**Frontend handler:** `addTranscriptEntry(msg.payload)`

---

## `mission:{id}:agents` — Heartbeat Format

Agent heartbeats published by the agent pool every 5 seconds:

```json
{
  "agent_id": "agent_2",
  "status": "BROWSING",
  "task_id": "uuid",
  "site_url": "reddit.com",
  "ts": 1710000010.0
}
```

---

## `mission:{id}:control` — Command Format

Orchestrator commands consumed by the agent pool:

```json
{
  "command": "REDIRECT",
  "agent_id": "agent_3",
  "task_id": "uuid",
  "objective": "Switch to searching GitHub for Sequoia AI portfolio repos",
  "ts": 1710000020.0
}
```

**`command` values:** `ASSIGN` | `REDIRECT` | `STOP`

---

## Implementation Notes

- Channel names are constructed by `backend/streaming/channels.py` helpers
- Publishing is done via `channels.publish(redis, mission_id, event_type, payload)`
- The WebSocket relay (`backend/streaming/ws_relay.py`) subscribes to `mission:{id}:events`
  and forwards every message as-is to connected browser clients
- The `useWebSocket.ts` hook in the frontend parses the top-level `type` field and
  dispatches to the appropriate Zustand store action
- All datetime values in payloads are ISO 8601 strings (UTC)
