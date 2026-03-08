# Mission Control — Tasks for Chinmay Shringi

**Role:** Voice Interface, Browser Agent System & Mission Planning Logic  
**GitHub:** [ChinmayShringi](https://github.com/ChinmayShringi) — 84 public repos  
**LinkedIn:** [chinmay-shringi](https://www.linkedin.com/in/chinmay-shringi/)  
**Website:** [chinmayshringi.web.app](https://chinmayshringi.web.app/)  
**Background:** Full-stack engineer — Python, TypeScript, Dart, browser automation, open-source contributor to fossology (compliance tool), AI hardware projects, blockchain. Active collaborator with teammates: contributes to sariyarizwan/neon-exchange and rahilsinghi/Coro.

---

## Implementation Status

**Last updated:** March 2026

| Task | Status | Notes |
|------|--------|-------|
| 3.1 Sonic Streaming Wrapper | ⏳ Pending | Needs Bedrock Nova Sonic model access |
| 3.2 Sonic Tool Schemas | ⏳ Pending | Depends on 3.1 |
| 3.3 Voice Gateway FastAPI + WS | ⏳ Pending | Depends on 3.1, 3.2, Manav's 4.2 — critical unblocking task for Sariya |
| 3.4 Audio Chunking + VAD | ⏳ Pending | Optional; skip for demo if time-pressed |
| 3.5 Barge-in / Interruption | ⏳ Pending | Depends on 3.3 |
| 5.1 Nova Act Session Manager | ⏳ Pending | Check current AgentCore Browser / Nova Act SDK availability |
| 5.2 Agent Pool | ⏳ Pending | Depends on 5.1, Manav's Redis (2.2) |
| 5.3 Agent Prompts (6 types) | ⏳ Pending | Can start now — `agents/prompts/` dir exists |
| 5.4 Evidence Emission | ⏳ Pending | Depends on 5.1, Rahil's `POST /evidence` (6.1) |
| 5.5 Agent Lifecycle + Heartbeat | ⏳ Pending | Depends on 5.2, 4.5 |
| 10.1 Task Decomposition Prompt | ⏳ Pending | Coordinate with Manav on `task_planner.py` (4.4) |
| 10.2 Task Graph Dependency Res. | ⏳ Pending | Depends on 4.4, 4.5 |
| 10.3 Agent-to-Task Assignment | ⏳ Pending | Depends on 5.2, 4.5 |
| 11.1 Agent Command Protocol | ⏳ Pending | Depends on 5.2, Manav's 4.5 |
| 11.2 Heartbeat Watchdog | ⏳ Pending | Depends on 5.5, 9.1 |
| 11.3 Parallel Deployment | ⏳ Pending | Depends on 11.1, 10.3 |

### What You Can Start Now

**Task 5.3 (Agent Prompts)** has no dependencies and can be done immediately — the `agents/prompts/` directory exists. Write the six `.txt` files and `__init__.py` loader. These are pure text files; no backend needed.

**Task 10.1 (Decomposition Prompt)** — the few-shot example for the Sequoia mission is already in your task spec. Write `agents/prompts/task_decomposition.txt` and coordinate with Manav so he can plug it into `task_planner.py` (Task 4.4).

### What You Need First

The foundation is already in place from Bharath (Phase 1):
- `backend/config.py` — `settings.BEDROCK_MODEL_SONIC`, `settings.AWS_REGION` ready
- `backend/main.py` — FastAPI app; mount your `voice_gateway.py` router here
- `backend/pyproject.toml` — `boto3`, `httpx`, `asyncpg`, `redis` already pinned

The UI is already built by Sariya (Phase 1 UI):
- `VoicePanel.tsx` — mic button, waveform, transcript feed — all wired to send to `/ws/voice`
- `useWebSocket.ts` — will connect to your `/ws/mission/{id}` endpoint automatically once it's live

### Coordination With Sariya

Your `/ws/voice` endpoint is what her VoicePanel connects to. Coordinate on:
- Message format: `{ "type": "VOICE_TRANSCRIPT", "role": "assistant", "text": "...", "is_final": bool }` — already matched in her `useWebSocket.ts` dispatch
- Audio format: PCM 16-bit 16 kHz — write `docs/VOICE_FORMAT.md` so she can configure `MediaRecorder` correctly

---

## Why These Tasks

Your breadth across Python backend and TypeScript, plus experience with browser-level tooling and open-source systems (fossology is production-grade browser-crawling adjacent work), makes you the right person to own the two most technically complex integration layers: the Voice Gateway (where Bedrock Sonic meets a live WebSocket) and the Browser Agent Fleet (where Nova Act sessions meet the orchestrator's command channel). You also own the task decomposition logic that bridges them.

---

## Task Summary

| Task | Phase | Description | Depends On | Status |
|------|-------|-------------|------------|--------|
| 3.1 | Voice | Bedrock Converse streaming wrapper (Sonic) | Phase 1, Bedrock access | ⏳ Pending |
| 3.2 | Voice | Sonic tool schema definitions | 3.1 | ⏳ Pending |
| 3.3 | Voice | Voice Gateway FastAPI + WebSocket | 3.1, 3.2, Phase 4 | ⏳ Pending |
| 3.4 | Voice | Audio chunking and VAD | 3.3 | ⏳ Pending |
| 3.5 | Voice | Barge-in / interruption handling | 3.3 | ⏳ Pending |
| 5.1 | Agents | Nova Act / AgentCore Browser session manager | Phase 2, Bedrock | ⏳ Pending |
| 5.2 | Agents | Agent pool and concurrency control | 5.1 | ⏳ Pending |
| 5.3 | Agents | Source-specialized agent prompts (6 types) | 5.1 | ⏳ Pending |
| 5.4 | Agents | Structured evidence emission interface | 5.1, Phase 6 | ⏳ Pending |
| 5.5 | Agents | Agent lifecycle and heartbeat | 5.2, 4.5 | ⏳ Pending |
| 10.1 | Planning | Task decomposition prompt engineering | 4.4 | ⏳ Pending |
| 10.2 | Planning | Task graph dependency resolution | 4.4, 4.5 | ⏳ Pending |
| 10.3 | Planning | Agent-to-task assignment algorithm | 5.2, 4.5 | ⏳ Pending |
| 11.1 | Orchestration | Agent command protocol | 5.2, 4.5 | ⏳ Pending |
| 11.2 | Orchestration | Heartbeat timeout watchdog | 5.5, 9.1 | ⏳ Pending |
| 11.3 | Orchestration | Parallel deployment (asyncio) | 11.1 | ⏳ Pending |

**Total: 16 tasks — 0 Done, 16 Pending**

---

## Coordination Map

| You need from | What |
|---------------|------|
| **Manav** | Redis (Task 2.2), Postgres (Task 2.3), Fargate/ALB (Task 2.1) before starting gateway; Nova Lite client (`models/lite_client.py` from Task 4.4); mission CRUD API (Task 4.2); Redis `publish_mission_event` helper (Task 9.1) |
| **Rahil** | Evidence ingest endpoint (`POST /evidence`, Task 6.1) — agents call this to emit findings; `deliver_final_briefing` internal endpoint needs the `POST /internal/deliver-briefing` contract defined with Rahil (Task 12.3) |
| **Bharath** | `backend/logging_config.py` and `backend/config.py` (Settings) from Phase 1 |
| **Sariya** | Your WebSocket relay (Task 9.2) and your voice WebSocket (Task 3.3) are the server-side contracts her frontend connects to |

---

## Full Task Details

---

### Task 3.1 — Bedrock Converse Streaming Wrapper (Sonic)

**Description:** Implement `models/sonic_client.py`: a thin async wrapper around Amazon Bedrock's `converse_stream` API for Nova 2 Sonic. This module yields streamed audio/text chunks and is the foundation for the Voice Gateway.

**Technical implementation notes:**
- File: `models/sonic_client.py`.
- Bedrock model ID for Nova 2 Sonic: read from `settings.BEDROCK_MODEL_SONIC`.
- Core function:
  ```python
  import boto3, json
  from typing import AsyncGenerator

  async def sonic_converse_stream(
      messages: list[dict],
      system: str,
      tools: list[dict] | None = None
  ) -> AsyncGenerator[dict, None]:
      client = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)
      request = {
          "modelId": settings.BEDROCK_MODEL_SONIC,
          "messages": messages,
          "system": [{"text": system}],
      }
      if tools:
          request["toolConfig"] = {"tools": tools}
      response = client.converse_stream(**request)
      for event in response["stream"]:
          yield event  # can contain contentBlockDelta, toolUse, messageStop, etc.
  ```
- Bedrock Converse stream events relevant for Sonic: `contentBlockDelta` (text or audio chunk), `toolUse` (when Sonic invokes a tool), `messageStop` (turn complete).
- Unit test: mock `boto3` client; assert that iterating the stream yields events in expected order.
- Note: Bedrock audio I/O for Sonic may require `audioConfig` in the request — check current Bedrock Nova Sonic docs for audio streaming specifics. If audio-in/audio-out is not available, fall back to text-in/text-out and use a separate TTS call for audio output.

**Dependencies:** Phase 1 completed (env config); Bedrock model access for Nova Sonic.

**Expected output:** `sonic_converse_stream(messages=[...])` yields at least one text chunk event; mock-tested.

---

### Task 3.2 — Sonic Tool Schema Definitions

**Description:** Define the five tool schemas that Sonic can invoke during a conversation. These schemas are injected into every Bedrock Converse request so Sonic knows what actions it can take without orchestrating directly.

**Technical implementation notes:**
- File: `models/sonic_tools.py`.
- Each tool as a dict matching Bedrock Converse `toolSpec` format:
  ```python
  SONIC_TOOLS = [
    {
      "toolSpec": {
        "name": "start_mission",
        "description": "Create and start a new intelligence mission based on the user's spoken objective. Call this as soon as you understand the user's request.",
        "inputSchema": {"json": {"type": "object", "properties": {"objective": {"type": "string", "description": "Full mission objective from user"}}, "required": ["objective"]}}
      }
    },
    {
      "toolSpec": {
        "name": "get_mission_status",
        "description": "Check the current status of a running mission, including agent count and evidence gathered so far.",
        "inputSchema": {"json": {"type": "object", "properties": {"mission_id": {"type": "string"}}, "required": ["mission_id"]}}
      }
    },
    {
      "toolSpec": {
        "name": "get_new_findings",
        "description": "Retrieve recent evidence findings for narration to the user.",
        "inputSchema": {"json": {"type": "object", "properties": {"mission_id": {"type": "string"}, "since_timestamp": {"type": "string", "description": "ISO timestamp; return findings after this time"}}, "required": ["mission_id"]}}
      }
    },
    {
      "toolSpec": {
        "name": "ask_user_for_clarification",
        "description": "Ask the user a clarifying question. Use only when the mission objective is truly ambiguous.",
        "inputSchema": {"json": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}
      }
    },
    {
      "toolSpec": {
        "name": "deliver_final_briefing",
        "description": "Deliver the completed intelligence briefing to the user as a spoken summary.",
        "inputSchema": {"json": {"type": "object", "properties": {"mission_id": {"type": "string"}, "briefing_text": {"type": "string"}}, "required": ["mission_id", "briefing_text"]}}
      }
    }
  ]
  ```
- Tool execution is handled in the gateway (Task 3.3), not in this module. This module is purely schemas.

**Dependencies:** Task 3.1.

**Expected output:** `SONIC_TOOLS` list importable; injected into every Converse request; Sonic can output `toolUse` events for these tool names.

---

### Task 3.3 — Voice Gateway FastAPI + WebSocket

**Description:** FastAPI service with a WebSocket endpoint `/ws/voice`. Receives binary audio from the browser, sends to Sonic, streams back text/audio. Executes Sonic tool calls in background asyncio tasks so response streaming is never blocked.

**Technical implementation notes:**
- File: `backend/gateway/voice_gateway.py` (or mounted on main FastAPI app at `/ws/voice`).
- WebSocket handler pseudocode:
  ```python
  @app.websocket("/ws/voice")
  async def voice_ws(ws: WebSocket):
      await ws.accept()
      messages = []
      mission_id = None
      async for raw in ws.iter_bytes():
          if raw == b'{"type":"interrupt"}':
              # Task 3.5
              break
          # Accumulate audio or parse JSON control
          messages.append({"role": "user", "content": [{"text": transcribe_or_pass(raw)}]})
          async for event in sonic_converse_stream(messages, system=SONIC_SYSTEM_PROMPT, tools=SONIC_TOOLS):
              if "contentBlockDelta" in event:
                  chunk = event["contentBlockDelta"]["delta"]
                  await ws.send_json({"type": "VOICE_TRANSCRIPT", "role": "assistant",
                                      "text": chunk.get("text", ""), "is_final": False})
              if "toolUse" in event:
                  tool = event["toolUse"]
                  asyncio.create_task(execute_tool(tool, ws, mission_id))
              if "messageStop" in event:
                  await ws.send_json({"type": "VOICE_TRANSCRIPT", "role": "assistant",
                                      "text": "", "is_final": True})
  ```
- `execute_tool(tool, ws, mission_id)`: dispatches to the correct handler:
  - `start_mission` → `POST /missions` (Manav's API); return mission_id to Sonic as tool result.
  - `get_mission_status` → `GET /missions/{id}`.
  - `get_new_findings` → `GET /missions/{id}/evidence?since=...`.
  - `ask_user_for_clarification` → send `VOICE_TRANSCRIPT` to client.
  - `deliver_final_briefing` → call `POST /internal/deliver-briefing` (Rahil's Task 12.3).
- After tool execution, inject tool result back into Sonic via next `converse_stream` call (role `tool`).
- Store per-mission conversation summary (last 2 exchanges) in Redis `LPUSH mission:{id}:conversation_summary <text> LTRIM 0 1`.
- Health route: `GET /health` → `{"status": "ok"}`.

**Dependencies:** Task 3.1, 3.2; Manav's Mission CRUD API (Task 4.2); Rahil's internal deliver-briefing endpoint (Task 12.3 — coordinate early).

**Expected output:** Browser sends audio chunks; Sonic responds with transcript events; `start_mission` tool creates a mission; mission_id returned to Sonic; tool calls fire without blocking voice stream.

---

### Task 3.4 — Audio Chunking and VAD (Optional)

**Description:** Optionally chunk client audio by silence using Voice Activity Detection before sending to Bedrock. Reduces unnecessary API calls during pauses and improves perceived latency.

**Technical implementation notes:**
- File: `backend/gateway/vad.py`.
- Use `webrtcvad` Python package (lightweight, pure Python/C). Mode 3 (most aggressive).
- Expected audio format from client: PCM 16-bit, 16 kHz mono (document in `docs/VOICE_FORMAT.md`).
- Frame size: 20 ms (320 bytes at 16 kHz 16-bit). Feed frames through VAD; buffer speech frames; emit chunk when silence detected (> 300 ms of silence = end of utterance).
- If VAD complexity is a concern for demo timeline, skip and accept raw chunks directly — Bedrock handles silence gracefully. Mark `DEMO_MODE` shortcut: skip VAD if `DEMO_MODE=true`.
- Client-side (for Sariya): document `MediaRecorder` settings: `mimeType = "audio/pcm"`, `audioBitsPerSecond = 256000`. Or use `AudioWorkletProcessor` for PCM extraction.

**Dependencies:** Task 3.3 (gateway must be running to plug VAD in).

**Expected output:** Optional VAD pipeline; `docs/VOICE_FORMAT.md` documents sample rate, bit depth, chunk size; unit test confirms silence frames are not forwarded.

---

### Task 3.5 — Barge-In / Interruption Handling

**Description:** When the user starts speaking while Sonic is still responding, accept an `interrupt` control message from the client, cancel the current Sonic stream, and begin a fresh turn with the new user utterance.

**Technical implementation notes:**
- Client sends: `ws.send(JSON.stringify({ "type": "interrupt" }))`.
- Gateway: maintain a `current_sonic_task: asyncio.Task` per WebSocket connection. On `interrupt`:
  1. Cancel `current_sonic_task`.
  2. Send `{ "type": "VOICE_TRANSCRIPT", "role": "assistant", "text": "", "is_final": true }` to client (end the current transcript visually).
  3. Clear any partial message from `messages` list that was mid-stream.
  4. Await new audio input to start fresh turn.
- Tag the interrupted response in the conversation summary so Nova Lite does not act on incomplete tool calls from the cancelled turn.
- Ensure `asyncio.CancelledError` is caught in the Sonic streaming task and cleans up gracefully.

**Dependencies:** Task 3.3.

**Expected output:** User can interrupt Sonic mid-speech; new utterance starts cleanly; no duplicate `start_mission` calls from a partially completed turn.

---

### Task 5.1 — Nova Act / AgentCore Browser Session Manager

**Description:** Integrate Amazon Bedrock AgentCore Browser (or Nova Act SDK) to spawn isolated browser sessions per agent. Implement session lifecycle: start, run objective, extract results, close.

**Technical implementation notes:**
- File: `agents/browser_session.py`.
- Check current Bedrock AgentCore Browser / Nova Act Python SDK. Primary API likely:
  ```python
  from nova_act import NovaAct  # or equivalent import

  async def run_browser_task(objective: str, agent_prompt: str, constraints: dict) -> BrowserResult:
      async with NovaAct(
          starting_page=constraints.get("starting_url", "https://google.com"),
          headless=True
      ) as agent:
          result = await agent.act(
              f"{agent_prompt}\n\nObjective: {objective}"
          )
          screenshot = await agent.screenshot()  # base64 PNG
          return BrowserResult(
              extracted_text=result.response,
              source_url=result.url,
              screenshot_base64=screenshot
          )
  ```
- `BrowserResult`: Pydantic model with `extracted_text`, `source_url`, `screenshot_base64`, `success: bool`.
- One session per `agent_id`; do not reuse sessions across tasks (isolation requirement).
- Store `session_id` in Redis `HSET agent:{id} session_id {sid}` with TTL matching task timeout.
- If Nova Act SDK is not yet available: fall back to `playwright` with `boto3` Bedrock `invoke_model` for reasoning. Document the fallback clearly.

**Dependencies:** Phase 2 infra; Bedrock AgentCore Browser access or Nova Act SDK installed.

**Expected output:** `run_browser_task("Find Sequoia's latest investments", OFFICIAL_SITE_PROMPT, {})` returns a `BrowserResult` with non-empty text and a screenshot; no session leaks.

---

### Task 5.2 — Agent Pool and Concurrency Control

**Description:** Maintain a fixed pool of 6 named agents (`agent_0` through `agent_5`). Track state in Redis. Prevent over-subscription; queue excess tasks.

**Technical implementation notes:**
- File: `agents/pool.py`.
- Redis agent state: `HSET agent:{id} status IDLE task_id "" session_id "" last_heartbeat {ts}`.
- On startup (`POST /missions` or service start): initialize all 6 agents to IDLE.
- `async def get_idle_agent(redis) -> str | None`: scan `agent_0..agent_5`; return first with `status == IDLE`; or None if all busy.
- `async def claim_agent(agent_id, task_id, redis)`: `HSET agent:{id} status ASSIGNED task_id {task_id}`. Use Redis `WATCH` + transaction to avoid race conditions if multiple planning loops run (demo: single loop, so this is simple).
- `async def release_agent(agent_id, redis)`: `HSET agent:{id} status IDLE task_id ""`.
- Pool size configurable via `settings.AGENT_POOL_SIZE = 6`.

**Dependencies:** Task 5.1; Manav's Redis (Task 2.2).

**Expected output:** All 6 agents initialized to IDLE on startup; `get_idle_agent` returns correctly; concurrent claim attempts do not double-assign; `release_agent` makes agent available again.

---

### Task 5.3 — Source-Specialized Agent Prompts

**Description:** Define one system prompt per agent type (6 total). Each prompt instructs the browser agent how to behave for its source domain. Store in `agents/prompts/`.

**Technical implementation notes:**
- Files: `agents/prompts/{agent_type}.txt` (lowercase). Six files:
  - `official_site.txt`: "You are a research agent focused on official company websites and investor relations pages. Navigate to the company's official domain. Prioritize: About pages, Team/Partners pages, Portfolio/Investments pages, Press releases. Extract: partner names with bios, investment thesis statements, recent portfolio companies (last 2 years). Be thorough but concise."
  - `news_blog.txt`: "You are a research agent focused on technology news and blog coverage. Search TechCrunch, VentureBeat, Forbes, Bloomberg Tech, and company blogs. Find articles from the last 18 months. Extract: investment announcements, partner quotes, strategy signals, fund size news."
  - `reddit_hn.txt`: "You are a sentiment research agent focused on Reddit and Hacker News. Allowed domains: reddit.com, news.ycombinator.com. Search for threads about the target company. Extract: founder complaints, positive/negative sentiment, specific anecdotes or quotes. Summarize the dominant sentiment."
  - `github.txt`: "You are a technical research agent focused on GitHub. Search for repositories owned by or associated with portfolio companies. Extract: technology stack, activity level (stars/commits), notable projects, open-source strategy signals."
  - `financial.txt`: "You are a financial data research agent. Check Crunchbase, PitchBook (if accessible), SEC EDGAR (for public filings), and financial news. Extract: fund sizes, investment amounts, valuation data, LP information if public."
  - `recent_news.txt`: "You are a breaking news research agent. Search Google News, Reuters, and AP News for coverage from the last 6 months only. Extract: recent strategic moves, new hires, product launches, controversies, regulatory actions."
- Loader: `agents/prompts/__init__.py` — `def load_prompt(agent_type: str) -> str: return open(f"agents/prompts/{agent_type.lower()}.txt").read()`.

**Dependencies:** Task 5.1 (prompts injected into session runner).

**Expected output:** Six prompt files; `load_prompt("REDDIT_HN")` returns correct text; orchestrator selects correct prompt per task's `agent_type`.

---

### Task 5.4 — Structured Evidence Emission

**Description:** After a browser task completes (via `run_browser_task`), parse the result and emit one or more structured evidence records to the Evidence Service. This is the critical bridge between agents and the evidence layer.

**Technical implementation notes:**
- File: `agents/evidence_emitter.py`.
- After `BrowserResult` returned from browser session:
  ```python
  async def emit_findings(result: BrowserResult, mission_id: UUID, agent_id: str, task_id: UUID):
      # Parse result.extracted_text into individual claims using Nova Lite
      claims = await extract_claims(result.extracted_text, mission_id, agent_id)
      for claim in claims:
          payload = {
              "mission_id": str(mission_id),
              "agent_id": agent_id,
              "claim": claim["claim"],
              "summary": claim["summary"],
              "source_url": str(result.source_url),
              "snippet": claim["snippet"],
              "screenshot_base64": result.screenshot_base64 if claim == claims[0] else None
          }
          async with httpx.AsyncClient() as client:
              await client.post(f"{settings.BACKEND_URL}/evidence", json=payload)
  ```
- `extract_claims(text, ...)`: call Nova Lite with prompt: `"Extract 2-5 distinct factual claims from this research text. Return JSON array: [{ \"claim\": str, \"summary\": str, \"snippet\": str }]"`. Parse and validate.
- Single screenshot uploaded only with first claim to avoid S3 cost; subsequent claims for same page have `screenshot_base64=None`.
- Emit `task_complete` signal to Redis after all claims posted: `LPUSH agent:{id}:findings '{"type":"TASK_COMPLETE","task_id":"..."}'` (consumed by Rahil's Task 11.4).

**Dependencies:** Task 5.1; Rahil's `POST /evidence` endpoint (Task 6.1) — coordinate on payload shape early.

**Expected output:** After running a browser task, 2-5 EvidenceRecord items appear in Postgres; `POST /evidence` returns 200 for each; screenshot attached to first record.

---

### Task 5.5 — Agent Lifecycle and Heartbeat

**Description:** Define the IDLE → ASSIGNED → BROWSING → REPORTING → IDLE state machine for agents. Implement heartbeat emission (agent side) that keeps Redis TTL alive while browsing.

**Technical implementation notes:**
- File: `agents/lifecycle.py`.
- States: stored in `HGET agent:{id} status`. Transitions:
  - IDLE → ASSIGNED: when orchestrator claims agent (Task 5.2).
  - ASSIGNED → BROWSING: when `run_browser_task` is called.
  - BROWSING → REPORTING: when browser task returns; evidence emission starts.
  - REPORTING → IDLE: when all claims posted; `release_agent` called.
- Heartbeat: while BROWSING, run `asyncio.create_task(heartbeat_loop(agent_id, redis))`:
  ```python
  async def heartbeat_loop(agent_id: str, redis):
      while True:
          await redis.set(f"agent:{agent_id}:heartbeat", "alive", ex=60)
          await asyncio.sleep(30)
  ```
- Cancel heartbeat task when entering REPORTING.
- Emit `AGENT_UPDATE` event to Redis on every state transition (consumed by Sariya's WebSocket relay):
  ```python
  await publish_mission_event(redis, mission_id, {
      "type": "AGENT_UPDATE",
      "agent_id": agent_id,
      "status": new_status,
      "task_id": str(task_id),
      "site_url": site_url
  })
  ```

**Dependencies:** Task 5.2; Manav's Task 4.5 (orchestrator triggers transitions); Manav's Task 9.1 (publish helper).

**Expected output:** Agent state visible in Redis at all times; heartbeat key present while agent is BROWSING; `AGENT_UPDATE` events appear on Redis channel.

---

### Task 10.1 — Task Decomposition Prompt Engineering

**Description:** Finalize and harden the Nova Lite prompt used by Manav's `task_planner.py` (Task 4.4) to decompose mission objectives into reliable, well-typed task lists. Your job is the prompt content and output validation — Manav wires it into the planner.

**Technical implementation notes:**
- File: `agents/prompts/task_decomposition.txt` (or inline in `task_planner.py` — coordinate with Manav).
- Few-shot examples embedded in the prompt. Example for Sequoia mission:
  ```
  Example Mission: "I'm pitching to Sequoia next week. Find their recent investments, partner priorities, founder complaints, and AI portfolio weaknesses."
  Output:
  [
    {"description": "Scrape sequoiacap.com for recent portfolio companies, partner bios, and investment thesis", "agent_type": "OFFICIAL_SITE", "priority": 10},
    {"description": "Search TechCrunch and VentureBeat for Sequoia investment announcements in 2024-2025", "agent_type": "NEWS_BLOG", "priority": 8},
    {"description": "Search Reddit and Hacker News for founder experiences and complaints about Sequoia", "agent_type": "REDDIT_HN", "priority": 7},
    {"description": "Find GitHub repositories of recent Sequoia AI portfolio companies", "agent_type": "GITHUB", "priority": 5},
    {"description": "Retrieve Sequoia's fund sizes and recent financial activity from Crunchbase", "agent_type": "FINANCIAL", "priority": 6},
    {"description": "Search for Sequoia AI investment strategy news from the last 6 months", "agent_type": "RECENT_NEWS", "priority": 9}
  ]
  ```
- Rules in prompt: always include at least one OFFICIAL_SITE task; never output more than 8 tasks; output valid JSON only; no markdown fences.
- Error recovery: if JSON parse fails, return a fallback list with a single OFFICIAL_SITE task. Add retry logic (attempt twice).

**Dependencies:** Manav's Task 4.4 (task graph construction wires this prompt).

**Expected output:** Any mission objective reliably produces 4–6 typed tasks; parse failure rate < 5% in unit tests across 10 test objectives.

---

### Task 10.2 — Task Graph Dependency Resolution

**Description:** Implement the logic that selects which tasks are "available" (all dependencies DONE) at each planning cycle. Used by the assignment algorithm (Task 10.3).

**Technical implementation notes:**
- File: `backend/orchestrator/task_graph.py`.
- Function: `def get_available_tasks(tasks: list[TaskNode]) -> list[TaskNode]`:
  ```python
  def get_available_tasks(tasks):
      done_ids = {t.id for t in tasks if t.status == "DONE"}
      return [
          t for t in tasks
          if t.status == "PENDING"
          and all(dep in done_ids for dep in (t.dependencies or []))
      ]
  ```
- Called in each planning cycle before the assignment algorithm.
- Task DONE condition: set by Rahil's aggregator (Task 11.4). Mark DONE when: (a) agent sends `TASK_COMPLETE` signal, or (b) evidence count for that task's theme >= `settings.TASK_EVIDENCE_THRESHOLD` (default 3).
- Topological sort (optional): if the task graph has complex dependencies, use `graphlib.TopologicalSorter` (Python 3.9+ stdlib). For demo, tasks are likely flat (no dependencies); keep it simple.

**Dependencies:** Manav's Task 4.4 (tasks created in DB), Task 4.5 (planning loop calls this).

**Expected output:** `get_available_tasks` returns only tasks whose dependencies are complete; changes each cycle as tasks are completed; prevents assigning tasks out of order.

---

### Task 10.3 — Agent-to-Task Assignment Algorithm

**Description:** Greedy priority assignment: given available tasks and idle agents, pair them optimally. Used by the orchestrator planning loop every cycle.

**Technical implementation notes:**
- File: `backend/orchestrator/assignment.py`.
- Function: `async def assign_tasks(available_tasks: list[TaskNode], redis) -> list[AssignAction]`:
  ```python
  async def assign_tasks(available_tasks, redis):
      idle_agents = await get_idle_agents(redis)  # list of agent_ids
      # Sort tasks by priority DESC, created_at ASC
      sorted_tasks = sorted(available_tasks, key=lambda t: (-t.priority, t.created_at))
      actions = []
      for task, agent_id in zip(sorted_tasks, idle_agents):
          # Prefer agent type match if possible
          actions.append(AssignAction(agent_id=agent_id, task_id=task.id, task=task))
      return actions
  ```
- Optional agent-type matching: prefer assigning a `REDDIT_HN` task to an agent that previously handled sentiment tasks (track last `agent_type` per agent in Redis). For demo: round-robin is sufficient.
- `AssignAction`: `{ agent_id, task_id, objective: task.description, agent_type: task.agent_type, constraints: {} }`.

**Dependencies:** Task 5.2 (`get_idle_agents`), Manav's Task 4.5 (planning loop calls this).

**Expected output:** Planning cycle produces a list of assignments; each assignment maps one task to one idle agent; no over-subscription.

---

### Task 11.1 — Agent Command Protocol

**Description:** Define the `AgentCommand` schema and implement the Redis-based command channel. The orchestrator pushes commands; agents consume them via blocking pop.

**Technical implementation notes:**
- File: `agents/command_channel.py`.
- Command schema (`agents/schemas.py`):
  ```python
  class CommandType(StrEnum):
      ASSIGN = "ASSIGN"
      REDIRECT = "REDIRECT"
      STOP = "STOP"

  class AgentCommand(BaseModel):
      command_type: CommandType
      agent_id: str
      task_id: UUID | None = None
      objective: str
      constraints: dict = {}
  ```
- Orchestrator pushes: `await redis.lpush(f"agent:{agent_id}:commands", command.model_dump_json())`.
- Agent consumer (runs in the agent worker process):
  ```python
  async def command_listener(agent_id: str, redis):
      while True:
          _, raw = await redis.brpop(f"agent:{agent_id}:commands", timeout=0)
          command = AgentCommand.model_validate_json(raw)
          await handle_command(command)
  ```
- `handle_command`: ASSIGN → update state to ASSIGNED, call `run_browser_task` + `emit_findings`; REDIRECT → cancel current task, update objective, restart browser; STOP → cancel task, set agent IDLE.
- Agent worker: each agent runs as an `asyncio` task or a separate process. For demo: all 6 agents run as tasks within the same Fargate process.

**Dependencies:** Task 5.2 (pool must exist); Manav's Task 4.5 (orchestrator produces commands); Manav's Redis (Task 2.2).

**Expected output:** Orchestrator can LPUSH a command; agent BRPOP picks it up within 100 ms; state updates correctly.

---

### Task 11.2 — Heartbeat Timeout Watchdog

**Description:** Background task that scans all agents every 30 s and reclaims any that have missed their heartbeat (Redis TTL expired). Marks the agent IDLE and its task PENDING for reassignment.

**Technical implementation notes:**
- File: `backend/orchestrator/watchdog.py`.
- Background task started on app startup:
  ```python
  async def watchdog(redis, db):
      while True:
          await asyncio.sleep(30)
          for i in range(settings.AGENT_POOL_SIZE):
              agent_id = f"agent_{i}"
              alive = await redis.get(f"agent:{agent_id}:heartbeat")
              status = await redis.hget(f"agent:{agent_id}", "status")
              if alive is None and status in ("ASSIGNED", "BROWSING"):
                  task_id = await redis.hget(f"agent:{agent_id}", "task_id")
                  # Reset agent
                  await redis.hset(f"agent:{agent_id}", mapping={"status": "IDLE", "task_id": ""})
                  # Reset task
                  if task_id:
                      await db.update_task_status(UUID(task_id), "PENDING")
                  # Emit timeline event
                  mission_id = await redis.hget(f"agent:{agent_id}", "mission_id")
                  await publish_mission_event(redis, UUID(mission_id), {
                      "type": "TIMELINE_EVENT",
                      "event_type": "agent_timeout",
                      "payload": {"agent_id": agent_id, "task_id": task_id}
                  })
                  # Increment metric (Manav's Task 13.2)
                  emit_metric("agent_heartbeat_missed_total", 1, agent_id=agent_id)
  ```
- Register as `asyncio.create_task(watchdog(redis, db))` in FastAPI `startup` event.

**Dependencies:** Task 5.5 (heartbeat must be emitting); Manav's Task 9.1 (publish helper).

**Expected output:** Kill a browser agent process mid-task (simulate crash); within 90 s, watchdog resets task to PENDING and agent to IDLE; next planning cycle reassigns.

---

### Task 11.3 — Parallel Deployment (asyncio)

**Description:** When the orchestrator produces multiple `AssignAction` items in one planning cycle, dispatch all agent commands in parallel. Do not block the planning loop while waiting for agents to acknowledge.

**Technical implementation notes:**
- File: add to `backend/orchestrator/planner.py` or `agents/command_channel.py`.
- In planning loop, after getting `actions = await assign_tasks(available_tasks, redis)`:
  ```python
  async def dispatch_commands(actions: list[AssignAction], redis, db):
      async with asyncio.TaskGroup() as tg:
          for action in actions:
              command = AgentCommand(
                  command_type=CommandType.ASSIGN,
                  agent_id=action.agent_id,
                  task_id=action.task_id,
                  objective=action.task.description,
                  constraints={}
              )
              tg.create_task(send_command(command, redis))
              tg.create_task(db.update_task_status(action.task_id, "ASSIGNED"))
              tg.create_task(claim_agent(action.agent_id, action.task_id, redis))
  ```
- `send_command`: `LPUSH agent:{id}:commands <JSON>`. Returns immediately — fire and forget (no ACK wait).
- Use `asyncio.TaskGroup` (Python 3.11+) for structured concurrency with clean error propagation.
- Target: all 6 agents launched within 3 s (the latency target from `tasks.md`).

**Dependencies:** Task 11.1 (command channel), Task 10.3 (assignment produces actions).

**Expected output:** Timing test: dispatch 6 commands and measure elapsed time; must be < 500 ms for all to be enqueued.

---

## Quick Reference — Files You Own

```
models/sonic_client.py
models/sonic_tools.py
backend/gateway/voice_gateway.py
backend/gateway/vad.py
docs/VOICE_FORMAT.md
agents/browser_session.py
agents/pool.py
agents/lifecycle.py
agents/evidence_emitter.py
agents/command_channel.py
agents/schemas.py
agents/prompts/
  official_site.txt
  news_blog.txt
  reddit_hn.txt
  github.txt
  financial.txt
  recent_news.txt
  task_decomposition.txt
  __init__.py
backend/orchestrator/
  task_graph.py
  assignment.py
  watchdog.py
```
