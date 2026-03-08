# Mission Control — Tasks for Sariya Rizwan

**Role:** War Room UI & Frontend Streaming  
**GitHub:** [sariyarizwan](https://github.com/sariyarizwan)  
**LinkedIn:** [sariyarizwan](https://www.linkedin.com/in/sariyarizwan/)  
**Background:** UI-focused engineer. Built [neon-exchange](https://github.com/sariyarizwan/neon-exchange) — a "NEON EXCHANGE pixel market city prototype" in TypeScript (full visual UI prototype, clearly design-forward). Also jobpilot (Python automation). Collaborates actively with Chinmay (neon-exchange) and Rahil (Coro).

---

## Implementation Status

**Last updated:** March 2026 — Session 6

| Task | Status | Notes |
|------|--------|-------|
| 8.1 React + Vite Scaffold | ✅ Done | Tailwind, postcss, clsx, lucide-react installed; `tsconfig.json` created; `npm run build` passes |
| 8.2 Full-Screen War Room Layout | ✅ Done | `WarRoomLayout.tsx` (CSS grid, 100vh), `Header.tsx` (brand, mission badge, connection dot) |
| 8.3 Voice Panel | ✅ Done | `VoicePanel.tsx` — mic toggle, 60fps canvas waveform via `requestAnimationFrame`, scrolling transcript feed |
| 8.4 Agent Fleet Grid | ✅ Done | `AgentGrid.tsx` + `AgentTile.tsx` + `StatusBadge.tsx` — 6 tiles, color-coded borders, scanning animation |
| 8.5 Evidence Board | ✅ Done | `EvidenceBoard.tsx` + `EvidenceCard.tsx` — theme filter pills, confidence meter, source links |
| 8.6 Mission Timeline | ✅ Done | `MissionTimeline.tsx` — all 7 event types with lucide-react icons, color-coded per type |
| 8.7 WebSocket Integration | ✅ Done | `useWebSocket.ts` written with exponential-backoff reconnection; wired to Zustand — backend WS endpoints now live |
| 9.2 WebSocket Relay (backend) | ✅ Done | `backend/streaming/ws_relay.py` — `/ws/mission/{id}` subscribes Redis, forwards to browser; 574 ms pipe confirmed |
| 9.3 Frontend Event Bus (Zustand) | ✅ Done | `src/store/index.ts` — all slices (mission, agents, evidence, timeline, transcript); `src/types/api.ts` — full TypeScript types |
| 9.4 Backpressure | ⏳ Pending | Batched flush + virtual scroll — implement once live WS is connected (it now is!) |
| 13.5 Dead-Letter Queue UI | ⏳ Pending | DLQ badge in header — `POST /evidence` ✅ is live; add `GET /internal/dlq/count` poll |

### Phase 1 UI — Complete ✅

The full War Room UI renders with mock data. Seeded with a live Sequoia demo mission: 4 active agents, 3 evidence cards across 3 themes, 7 timeline events, 2 transcript entries. Theme filter, confidence meters, and scanning animations all work.

Run: `cd frontend && npm run dev` → http://localhost:5173 (or next available port).

### Session 5 — Backend Live, Connect UI ⬅️ Your Next Step

Both backend WebSocket endpoints are now live:
- `/ws/voice` (Chinmay) ✅
- `/ws/mission/{id}` (Bharath) ✅ — 574 ms event pipe confirmed

**Session 6 — EVIDENCE_FOUND payload fix (already applied):** In `useWebSocket.ts`, the backend publishes `EVIDENCE_FOUND` with the evidence object **directly as `payload`**, not nested under `payload.evidence`. The hook was updated from `addEvidence(msg.payload.evidence)` to `addEvidence(msg.payload)` so new evidence cards appear correctly when events stream in. The backend also sends a `created_at` alias so `EvidenceCard`'s timestamp display works.

**Your immediate next step (Session 6):** Wire the War Room UI to the live backend:
1. In `store/index.ts`, replace the hardcoded mock `missionId` with the UUID returned from `POST /missions`.
2. The `useWebSocket.ts` hook will then auto-connect to `/ws/mission/{real-id}` and drive all state from live Redis events (EVIDENCE_FOUND now handled correctly).
3. `POST /evidence` is live — you can test the full evidence streaming pipeline end-to-end right now.

### Blocked On / Next Steps

- **Live backend connection** — swap mock `missionId` in Zustand store with real UUID from `POST /missions localhost:8000/missions`. The `useWebSocket` hook is already wired correctly.
- **9.4 Backpressure:** Add `src/hooks/useThrottledStore.ts` now that there's a real event stream to measure. Also add `@tanstack/react-virtual` to Evidence Board.
- **13.5 DLQ badge:** Add `GET /internal/dlq/count` poll to `Header.tsx`. `POST /evidence` is live — just needs the DLQ endpoint added to the backend.

---

## Why These Tasks

Your neon-exchange project — a pixel art market city prototype — is exactly the aesthetic and technical instinct Mission Control's War Room needs: cinematic, real-time, data-driven UI. You own everything the user sees: the full-screen dark war room layout, the live agent grid, the evidence board that streams in cards, the voice panel with a waveform, and the mission timeline. You also own the frontend streaming architecture (Zustand store, WebSocket state, backpressure) and the dead-letter / retry observability that surfaces errors silently in the UI.

---

## Task Summary

| Task | Phase | Description | Depends On | Status |
|------|-------|-------------|------------|--------|
| 8.1 | War Room UI | React + Vite scaffold | 1.2 | ✅ Done |
| 8.2 | War Room UI | Full-screen War Room layout | 8.1 | ✅ Done |
| 8.3 | War Room UI | Voice panel (mic, waveform, transcript) | 8.2, Phase 9 (WS) | ✅ Done |
| 8.4 | War Room UI | Agent Fleet Grid (live tiles) | 8.2, Phase 9 | ✅ Done |
| 8.5 | War Room UI | Evidence Board (streaming cards) | 8.2, 6.4 ✅, Phase 9 | ✅ Done |
| 8.6 | War Room UI | Mission Timeline (event log) | 8.2, Phase 9 | ✅ Done |
| 8.7 | War Room UI | WebSocket integration + reconnection | 8.3–8.6 | ✅ Done |
| 9.2 | Streaming | WebSocket relay (backend → frontend) | 9.1 ✅, 3.3 ✅ | ✅ Done |
| 9.3 | Streaming | Frontend event bus and state (Zustand) | 8.1, 9.2 ✅ | ✅ Done |
| 9.4 | Streaming | Backpressure and rate limiting | 9.2 ✅, 9.3 ✅ | ⏳ Pending |
| 13.5 | Observability | Dead-letter queue and retry strategy | 6.1 ✅, 11.1 | ⏳ Pending |

**Total: 11 tasks — 9 Done, 2 Pending**

---

## Coordination Map

| You need from | What |
|---------------|------|
| **Chinmay** | ~~Voice Gateway WebSocket (`/ws/voice`, Task 3.3)~~ ✅ **Done** |
| **Bharath** | ~~Mission REST API (`GET/POST /missions`, Task 4.2)~~ ✅ **Done** · ~~Redis channels (`docs/EVENTS.md`, Task 9.1)~~ ✅ **Done** · ~~WS relay (`/ws/mission/{id}`, Task 9.2)~~ ✅ **Done** |
| **Rahil** | ~~Evidence list API (`GET /missions/{id}/evidence`, Task 6.4)~~ ✅ **Done** · Presigned screenshot URLs (Task 6.2) — still pending |
| **Manav** | ALB URL and CORS config for production deployment (Task 2.1) — still pending |

---

## Full Task Details

---

### Task 8.1 — React + Vite Scaffold

**Description:** Initialize the `frontend/` project with Vite, React 18, and TypeScript. Configure environment variables, path aliases, Zustand state, and a placeholder WebSocket hook. This unblocks all other UI work.

**Technical implementation notes:**
- Bootstrap: `npm create vite@latest . -- --template react-ts` (run inside `frontend/`).
- Additional packages: `zustand`, `@tanstack/react-query`, `clsx`, `tailwindcss`, `postcss`, `autoprefixer`, `@radix-ui/react-*` (for accessible primitives), `lucide-react` (icons), `framer-motion` (animations for the war room feel).
- `vite.config.ts`: path alias `@/` → `./src/`, proxy `/api` to `VITE_API_URL` (dev only).
- `.env.example` (frontend): `VITE_API_URL=http://localhost:8000`, `VITE_WS_URL=ws://localhost:8000`.
- `tailwind.config.ts`: extend theme with war room colors: `background: "#030712"`, `surface: "#0f172a"`, `accent: { green: "#22c55e", amber: "#f59e0b", red: "#ef4444", blue: "#3b82f6" }`.
- `src/store/index.ts`: placeholder Zustand store with empty slices (filled in Task 9.3).
- `src/hooks/useWebSocket.ts`: placeholder hook (filled in Task 8.7).
- `src/App.tsx`: renders `<WarRoomLayout />`.

**Dependencies:** Bharath's Task 1.2 (package.json base); Bharath's `VITE_*` env vars (Task 1.3).

**Expected output:** `npm run dev` runs at `localhost:5173`; blank dark page; TypeScript compiles clean; Tailwind purges correctly in `npm run build`.

**Subtasks:**
- 8.1.1 Vite + React + TypeScript init; install all deps.
- 8.1.2 Tailwind config with war room theme.
- 8.1.3 Path aliases, env config, Vite proxy.
- 8.1.4 Placeholder Zustand store and WebSocket hook.

---

### Task 8.2 — Full-Screen War Room Layout

**Description:** Design and implement the dark, full-screen "war room" layout with distinct regions. No dynamic data yet — only structure and visual identity. This is the canvas for all other UI tasks.

**Technical implementation notes:**
- File: `src/components/layout/WarRoomLayout.tsx`.
- Layout: CSS Grid, `100vw × 100vh`, no scrollbars on the outer container.
  ```
  ┌─────────────────────────────────────┐
  │          MISSION HEADER (h: 48px)   │
  ├────────────────┬────────────────────┤
  │  AGENT FLEET   │  EVIDENCE BOARD    │
  │  GRID          │  (scrollable)      │
  │  (60% width)   │  (40% width)       │
  ├────────────────┴────────────────────┤
  │  VOICE PANEL (h: 140px)             │
  └─────────────────────────────────────┘
  ```
  Mission Timeline: collapsible sidebar on the right edge, or drawer triggered by a button.
- CSS classes (Tailwind):
  - Outer: `bg-[#030712] text-slate-100 h-screen w-screen grid overflow-hidden`
  - Grid rows: `grid-rows-[48px_1fr_140px]`
  - Header: `border-b border-slate-800 flex items-center justify-between px-6`
  - Agent grid: `overflow-hidden`
  - Evidence board: `border-l border-slate-800 overflow-y-auto`
  - Voice panel: `border-t border-slate-800`
- Visual polish: subtle scanline overlay (`radial-gradient` or CSS `after` pseudo-element), monospace font for status text (e.g. `JetBrains Mono` via Google Fonts), green accent for active states.
- Placeholder text in each region: "AGENT FLEET", "EVIDENCE BOARD", "MISSION TIMELINE".

**Dependencies:** Task 8.1.

**Expected output:** Full-screen dark layout visible; grid proportions correct on 1920×1080 and 1440×900; no layout breaks on resize.

---

### Task 8.3 — Voice Panel

**Description:** The voice panel at the bottom of the war room. Includes microphone button (push-to-talk), animated waveform during speech, scrolling transcript of user + assistant turns. Connects to Chinmay's Voice Gateway WebSocket.

**Technical implementation notes:**
- File: `src/components/VoicePanel.tsx`.
- Subcomponents: `MicButton`, `Waveform`, `TranscriptFeed`.
- `MicButton`: toggle mic on/off. On activate: `navigator.mediaDevices.getUserMedia({ audio: true })`, create `MediaRecorder`, send chunks via WebSocket. On `interrupt`: send `JSON.stringify({ "type": "interrupt" })` over WS. Visual: pulsing ring when active (Framer Motion `scale` animation).
- `Waveform`: use `Web Audio API` `AnalyserNode` to read frequency data from mic stream; render via `<canvas>` with 60 fps `requestAnimationFrame`. Bar chart or oscilloscope style. Color: `#22c55e` (green) when speaking, `#3b82f6` (blue) when assistant is responding.
- `TranscriptFeed`: scrollable list of `{ role, text }` items from Zustand store. Auto-scrolls to bottom on new item. User turns right-aligned in green, assistant turns left-aligned in blue/white. Fade-in animation per new entry.
- Audio playback (optional for demo): if backend streams audio bytes via WebSocket, use `AudioContext.decodeAudioData` and `AudioBufferSourceNode`. Otherwise text-only transcript.
- Client audio format: PCM 16-bit 16 kHz (coordinate with Chinmay's `docs/VOICE_FORMAT.md`). If browser doesn't support raw PCM, use `AudioWorkletProcessor` to convert from `Float32Array`.

**Dependencies:** Task 8.2 (layout region); Task 8.7 (WebSocket hook); Chinmay's Voice Gateway (Task 3.3 — use mock during dev).

**Expected output:** User clicks mic; waveform animates; browser sends audio chunks over WebSocket; `VOICE_TRANSCRIPT` events appear as scrolling transcript entries.

---

### Task 8.4 — Agent Fleet Grid

**Description:** Grid of 6 agent tiles in the center of the war room. Each tile shows the agent's name, status badge, current objective, site URL, and optionally a live screenshot thumbnail. Updates in real-time from WebSocket `AGENT_UPDATE` events.

**Technical implementation notes:**
- File: `src/components/AgentGrid.tsx` + `src/components/AgentTile.tsx`.
- Initial state: read from Zustand `agents[]` slice. On mount: also `GET /agents` to populate initial state.
- `AgentTile` layout: dark card (`bg-slate-900 border border-slate-700 rounded-lg p-3`). Contents:
  - Top row: `agent_id` monospace label + `StatusBadge` component.
  - `StatusBadge`: color-coded pill — IDLE (`slate`), ASSIGNED (`amber`), BROWSING (`blue`), REPORTING (`green`). Pulse animation when BROWSING.
  - Objective text: truncated to 2 lines, `text-slate-300 text-sm`.
  - Site URL: truncated, linked, `text-blue-400 text-xs`.
  - Screenshot thumbnail: if `screenshot_url` in event, render `<img>` with object-fit cover. Otherwise, animated "scanning" placeholder (CSS skeleton or gradient sweep).
- Animation: when tile transitions from IDLE to ASSIGNED, trigger a brief border flash (`border-amber-400 → border-slate-700`) via Framer Motion layout animation.
- Live browser preview via iframe: only if backend exposes a live browser viewport URL (out of scope for demo). Use screenshot thumbnail instead.

**Dependencies:** Task 8.2 (grid region); Task 9.3 (Zustand `agents[]` slice); Manav's `GET /agents` endpoint (Task 4.2).

**Expected output:** 6 agent tiles visible; status and objective update in real time via WebSocket; screenshot thumbnail renders when available.

---

### Task 8.5 — Evidence Board

**Description:** The scrollable evidence board on the right side of the war room. Streams in evidence cards as `EVIDENCE_FOUND` WebSocket events arrive. Cards grouped or filterable by theme. Each card shows claim, summary, source link, snippet, confidence meter, theme pill, and screenshot thumbnail.

**Technical implementation notes:**
- File: `src/components/EvidenceBoard.tsx` + `src/components/EvidenceCard.tsx`.
- On mount: `GET /missions/{id}/evidence` (Rahil's Task 6.4) to hydrate initial state.
- New cards: appended at top (most recent first) when `EVIDENCE_FOUND` event arrives. Animate in with `framer-motion` `initial={{ opacity: 0, y: -20 }}` → `animate={{ opacity: 1, y: 0 }}`.
- `EvidenceCard` layout (masonry or stacked grid):
  - Header: `theme` pill (`bg-blue-900 text-blue-300 text-xs rounded-full px-2`), `confidence` badge (e.g. "92%").
  - Body: `claim` in bold (`text-white font-medium`), `summary` in muted (`text-slate-400 text-sm`).
  - Footer: source link (`truncated, text-blue-400`), timestamp.
  - Thumbnail: `<img src={screenshot_url} />` with `object-cover` at fixed height; lazy-load.
  - Confidence meter: `<progress>` or a custom div with width = `confidence * 100%`; green for > 0.8, amber for > 0.6, red below.
- Theme filter bar at top of Evidence Board: pills for each unique theme in evidence. Click to filter (`?theme=X`). "All" pill clears filter.
- Virtual scroll: use `@tanstack/react-virtual` if evidence count > 50 to prevent DOM bloat.

**Dependencies:** Task 8.2; Task 9.3 (evidence slice in Zustand); Rahil's Task 6.4 (`GET /missions/{id}/evidence`) and Task 6.2 (presigned screenshot URLs).

**Expected output:** Evidence cards stream in during demo; theme filter correctly hides/shows cards; screenshot thumbnails load; list stays performant at 50+ cards.

---

### Task 8.6 — Mission Timeline

**Description:** Chronological event log showing every significant mission event: agent deployed, evidence found, agent redirected, contradiction detected, synthesis started, mission complete. Consumes `TIMELINE_EVENT` WebSocket events.

**Technical implementation notes:**
- File: `src/components/MissionTimeline.tsx`.
- Render as a vertical list, newest events at top. Each event: timestamp, icon, description.
- Event types and display:
  - `agent_assigned`: "Agent {id} assigned to {task_type}" — icon: robot, color: amber.
  - `evidence_found`: "New finding: {claim truncated}" — icon: document, color: green.
  - `agent_redirected`: "Agent {id} redirected to {new_objective}" — icon: arrow, color: blue.
  - `agent_timeout`: "Agent {id} timed out — task reassigned" — icon: warning, color: red.
  - `synthesis_start`: "Synthesizing intelligence..." — icon: sparkle, color: purple.
  - `mission_complete`: "Mission complete" — icon: checkmark, color: green, larger text.
  - `contradiction_detected`: "Contradiction flagged: {description}" — icon: exclamation, color: red.
- Container: collapsible `<aside>` panel or bottom-of-screen `<section>`. Default visible in demo.
- Use `lucide-react` for icons (Bot, FileText, ArrowRight, AlertTriangle, Sparkles, CheckCircle).
- Animate each new event in with `framer-motion`.

**Dependencies:** Task 8.2; Task 9.3 (`timeline[]` slice in Zustand).

**Expected output:** Timeline fills progressively during mission; each event type renders with correct icon and color; newest event always visible.

---

### Task 8.7 — WebSocket Integration and Reconnection

**Description:** Centralized WebSocket hook managing connections to both the voice WebSocket and the mission event WebSocket. Handles reconnection with exponential backoff; on reconnect, refetches mission state to fill gaps.

**Technical implementation notes:**
- File: `src/hooks/useWebSocket.ts`.
- Two connections per session:
  1. `/ws/voice` — voice audio + transcript events.
  2. `/ws/mission/{mission_id}` — all mission events (AGENT_UPDATE, EVIDENCE_FOUND, etc.).
- Connection state: `"connecting" | "open" | "closed" | "error"`.
- Reconnection: exponential backoff starting at 1 s, max 30 s, jitter ± 0.5 s. Reset on successful open.
  ```typescript
  const reconnect = useCallback(() => {
    const delay = Math.min(baseDelay * 2 ** attempts, 30000) + Math.random() * 500;
    setTimeout(() => { attempts++; connect(); }, delay);
  }, [attempts]);
  ```
- On reconnect: call `GET /missions/{mission_id}` to refetch current state; merge with Zustand store (Rahil's evidence list + Manav's mission status). Avoid duplicating events by tracking last seen event timestamp.
- Show connection status indicator in top bar: green dot = connected, amber = reconnecting, red = error.
- Voice WebSocket: also send `{ "type": "start" }` on connect and `{ "type": "stop" }` on disconnect.

**Dependencies:** Tasks 8.3–8.6 (all use this hook); Task 9.3 (dispatches to store); Chinmay's gateway (Task 3.3).

**Expected output:** WebSocket reconnects automatically after network drop; UI shows correct status dot; no duplicate evidence cards after reconnect.

---

### Task 9.2 — WebSocket Relay (Backend → Frontend)

**Description:** FastAPI WebSocket endpoint `/ws/mission/{mission_id}` that subscribes to the Redis `mission:{mission_id}:events` channel and forwards every message to the connected client. This is the server-side bridge for all real-time UI events.

**Technical implementation notes:**
- File: `backend/gateway/ws_relay.py`.
- Handler:
  ```python
  @app.websocket("/ws/mission/{mission_id}")
  async def mission_ws(ws: WebSocket, mission_id: UUID, redis=Depends(get_redis)):
      await ws.accept()
      # Send initial state
      mission = await db.get_mission(mission_id)
      await ws.send_json({"type": "MISSION_STATUS", "payload": mission.model_dump()})
      # Subscribe to Redis channel
      pubsub = redis.pubsub()
      await pubsub.subscribe(f"mission:{mission_id}:events")
      try:
          async for message in pubsub.listen():
              if message["type"] == "message":
                  await ws.send_text(message["data"])
      except WebSocketDisconnect:
          await pubsub.unsubscribe(f"mission:{mission_id}:events")
  ```
- Also subscribe to `agent:{id}:findings` for all agents in the mission so evidence cards stream in.
- Map Redis event format directly to WS message format from `tasks.md` API contracts.
- Handle `WebSocketDisconnect`: unsubscribe from Redis, cancel asyncio task cleanly.
- Auth: verify `X-API-Key` or session token (same as REST API guard).

**Dependencies:** Manav's Redis pub/sub channels (Task 9.1); Manav's Mission CRUD (Task 4.2 for initial state on connect).

**Expected output:** Browser connects to `/ws/mission/{id}` and receives all events live; `AGENT_UPDATE` and `EVIDENCE_FOUND` events arrive within 200 ms of Redis publish; reconnect works correctly.

---

### Task 9.3 — Frontend Event Bus and State (Zustand)

**Description:** Implement the Zustand store with slices for mission, agents, evidence, and timeline. WebSocket handler dispatches events into the store; all UI components read from the store reactively.

**Technical implementation notes:**
- File: `src/store/index.ts`.
- Zustand store with slices (use `create` with Immer middleware for clean mutations):
  ```typescript
  interface MissionStore {
    mission: MissionRecord | null;
    agents: AgentState[];
    evidence: EvidenceRecord[];
    timeline: TimelineEvent[];
    connectionStatus: "connecting" | "open" | "closed" | "error";

    // Actions
    setMission: (m: MissionRecord) => void;
    updateAgent: (update: AgentUpdate) => void;
    addEvidence: (e: EvidenceRecord) => void;
    addTimelineEvent: (ev: TimelineEvent) => void;
    setConnectionStatus: (s: ConnectionStatus) => void;
  }
  ```
- `updateAgent`: find agent by `agent_id`; merge fields. If not found: append (new agent tile).
- `addEvidence`: prepend to `evidence[]`; deduplicate by `id` to prevent duplicates after reconnect.
- WebSocket event dispatcher (in `useWebSocket.ts`):
  ```typescript
  const dispatch = useMissionStore();
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    switch (msg.type) {
      case "AGENT_UPDATE": dispatch.updateAgent(msg.payload); break;
      case "EVIDENCE_FOUND": dispatch.addEvidence(msg.payload.evidence); break;
      case "MISSION_STATUS": dispatch.setMission(msg.payload); break;
      case "TIMELINE_EVENT": dispatch.addTimelineEvent(msg.payload); break;
      case "VOICE_TRANSCRIPT": dispatch.addTranscriptEntry(msg); break;
    }
  };
  ```
- TypeScript interfaces in `src/types/api.ts` matching `tasks.md` schemas exactly (coordinate with Manav and Rahil on field names).

**Dependencies:** Task 8.1 (Zustand installed); Task 9.2 (WebSocket relay sends messages).

**Expected output:** Any WebSocket message updates the store; component using `useMissionStore()` re-renders correctly; no stale state after reconnect.

---

### Task 9.4 — Backpressure and Rate Limiting

**Description:** Prevent the Evidence Board and Timeline from freezing the browser tab when evidence arrives at high rate during demo. Batch updates and cap render frequency.

**Technical implementation notes:**
- File: `src/hooks/useThrottledStore.ts` and edits to `useWebSocket.ts`.
- Strategy: **event queue + batched flush**:
  ```typescript
  const eventQueue: WSMessage[] = [];

  ws.onmessage = (e) => eventQueue.push(JSON.parse(e.data));

  // Flush every 150ms
  setInterval(() => {
    if (eventQueue.length === 0) return;
    const batch = eventQueue.splice(0, eventQueue.length);
    // Batch dispatch: collapse multiple AGENT_UPDATEs for same agent_id
    const collapsed = collapseBatch(batch);
    collapsed.forEach(dispatch);
  }, 150);
  ```
- `collapseBatch`: for AGENT_UPDATE events with the same `agent_id`, keep only the latest. For EVIDENCE_FOUND, keep all (unique by id).
- Evidence Board: use `@tanstack/react-virtual` for virtualized rendering (Task 8.5 already notes this).
- Rate cap: if queue grows > 100 events (burst), skip rendering EVIDENCE_FOUND for that flush cycle but always process MISSION_STATUS and AGENT_UPDATE (mission-critical).
- Document the strategy in `docs/FRONTEND_STREAMING.md`.

**Dependencies:** Task 9.2 (messages arriving); Task 9.3 (store dispatching).

**Expected output:** Tab stays at 60 fps under burst of 20 evidence events/s; no dropped MISSION_STATUS or AGENT_UPDATE events; `docs/FRONTEND_STREAMING.md` committed.

---

### Task 13.5 — Dead-Letter Queue and Retry Strategy

**Description:** Implement the backend DLQ for failed evidence ingestion, and add a UI indicator in the War Room header showing failed/retried events so the team can debug during the demo.

**Technical implementation notes:**
- **Backend** (`backend/evidence/dlq.py`):
  - On `POST /evidence` failure (DB error, validation error): catch exception; `LPUSH mission-control:dlq <EvidenceIngest JSON>` in Redis. Log with `structlog` at ERROR level with `mission_id`, `agent_id`, error type.
  - Background retry worker: every 30 s, `LRANGE mission-control:dlq 0 9`; retry each up to 3 times with exponential backoff (1 s, 2 s, 4 s). On success: `LREM mission-control:dlq 0 <item>`. On 3rd failure: log and discard.
  - Agent command failures (Task 11.1): if `LPUSH agent:{id}:commands` fails (Redis down), log and mark task PENDING again. Retry ASSIGN once on next planning cycle; if second failure, set task FAILED and emit TIMELINE_EVENT.
- **Frontend** (`src/components/layout/Header.tsx`):
  - DLQ size indicator: poll `GET /internal/dlq/count` every 10 s (add this tiny endpoint to backend: `LLEN mission-control:dlq`). If > 0, show amber warning badge in header: "3 pending retries".
  - Retry button (optional): `POST /internal/dlq/flush` — triggers immediate retry of all DLQ items.
  - Document in `docs/OBSERVABILITY.md`.

**Dependencies:** Rahil's Task 6.1 (evidence ingest is the main DLQ producer); Chinmay's Task 11.1 (agent commands are secondary DLQ concern).

**Expected output:** If Postgres is briefly unavailable, evidence does not silently drop; DLQ fills; retry succeeds when DB recovers; header shows warning badge; cleared when DLQ drains.

---

## Design Reference

### Color Palette (Tailwind)

| Token | Hex | Use |
|-------|-----|-----|
| `background` | `#030712` | Page background |
| `surface` | `#0f172a` | Cards, panels |
| `border` | `#1e293b` | Dividers |
| `text-primary` | `#f8fafc` | Headings |
| `text-secondary` | `#94a3b8` | Body / labels |
| `accent-green` | `#22c55e` | Active agents, success, mic active |
| `accent-amber` | `#f59e0b` | Assigned agents, warnings |
| `accent-red` | `#ef4444` | Errors, timeouts, contradictions |
| `accent-blue` | `#3b82f6` | Browsing agents, links |
| `accent-purple` | `#a855f7` | Synthesis in progress |

### Typography

- Headings: Inter or system-ui
- Status text / IDs / URLs: JetBrains Mono (load via `@fontsource/jetbrains-mono`)
- Body: Inter 14px

### Animation Principles

- Agent status change: 200 ms border flash + badge color transition
- Evidence card append: 300 ms slide-in from top with fade
- Timeline event: 200 ms fade-in
- Mic active: subtle pulse ring (2 s loop)
- Waveform: 60 fps via `requestAnimationFrame` + `AnalyserNode`

---

## Quick Reference — Files You Own

```
frontend/
  src/
    App.tsx
    store/index.ts
    types/api.ts
    hooks/
      useWebSocket.ts
      useThrottledStore.ts
    components/
      layout/
        WarRoomLayout.tsx
        Header.tsx
      VoicePanel.tsx
      MicButton.tsx
      Waveform.tsx
      TranscriptFeed.tsx
      AgentGrid.tsx
      AgentTile.tsx
      StatusBadge.tsx
      EvidenceBoard.tsx
      EvidenceCard.tsx
      MissionTimeline.tsx
  tailwind.config.ts
  vite.config.ts
backend/gateway/ws_relay.py
backend/evidence/dlq.py
backend/routers/internal.py      (DLQ count + flush endpoints)
docs/FRONTEND_STREAMING.md
docs/OBSERVABILITY.md
```
