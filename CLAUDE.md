# Mission Control (Dispatch) — Getting Started Guide

This file is the single source of truth for getting your local environment running and starting work on your assigned tasks.

---

## Current Implementation Status

**Last updated:** March 2026 — Session 8

### What Is Done

| Area | Status | Key Files |
|------|--------|-----------|
| Monorepo scaffold | ✅ Done | All dirs, `.gitignore`, `README.md` |
| Backend deps | ✅ Done | `backend/pyproject.toml` (13 runtime deps + dev extras) |
| Frontend deps | ✅ Done | `frontend/package.json`, `package-lock.json`, `tsconfig.json` |
| Env config | ✅ Done | `.env.example` (18 vars incl. `NOVA_API_KEY`, `AWS_BEARER_TOKEN_BEDROCK`), `docs/ENV.md`, `backend/config.py` |
| CI pipeline | ✅ Done | `.github/workflows/ci.yml` (4 parallel jobs, green) |
| Backend health endpoint | ✅ Done | `GET /health → {"status": "ok"}` in `backend/main.py` |
| Backend smoke test | ✅ Done | `backend/tests/test_smoke.py` — passing |
| Backend integration tests | ✅ Done | `backend/tests/test_integration.py` — 43 tests (mission CRUD, state machine, evidence, WS relay) |
| War Room UI | ✅ Done | Full dark war room layout, all panels rendered with mock data |
| TypeScript types | ✅ Done | `frontend/src/types/api.ts` — all schemas (Mission, Agent, Evidence, Timeline) |
| Zustand store | ✅ Done | `frontend/src/store/index.ts` — seeded with Sequoia demo mission |
| WebSocket hook | ✅ Done | `frontend/src/hooks/useWebSocket.ts` — reconnection logic ready; connects to live `/ws/mission/{id}` |
| Nova Sonic client | ✅ Done | `backend/models/sonic_client.py` — real-time WebSocket voice client, smoke-tested live |
| Sonic tool schemas | ✅ Done | `backend/models/sonic_tools.py` — 5 tools in Nova Realtime + Bedrock formats |
| Nova Lite client | ✅ Done | `backend/models/lite_client.py` — chat, streaming, plan_tasks, plan_next_actions, smoke-tested live |
| Docker Compose | ✅ Done | `docker-compose.yml`, `infra/init.sql`, `Makefile` — Redis + Postgres + MinIO |
| Mission CRUD API | ✅ Done | `backend/missions/` — schemas, repository, router; `POST /missions` calls Nova Lite + stores task graph |
| Evidence Ingest API | ✅ Done | `backend/evidence/` — schemas, repository, router; `POST /evidence` + `GET /missions/{id}/evidence` |
| Redis Channels | ✅ Done | `backend/streaming/channels.py` — channel helpers + `publish()`; `docs/EVENTS.md` full spec |
| WS Mission Relay | ✅ Done | `backend/streaming/ws_relay.py` — `/ws/mission/{id}` subscribes Redis, forwards to browser; 574 ms pipe confirmed |
| Voice Gateway | ✅ Done | `backend/gateway/voice_gateway.py` — `/ws/voice` bidirectional Nova Sonic bridge; all 5 tool handlers wired |
| AWS Infra | ✅ Done | Manav — Tasks 2.1–2.7 (CDK stacks for VPC, ECS, Redis, RDS, S3, OpenSearch, IAM + Docker Compose) |
| Browser Agents | ✅ Done | Chinmay — Tasks 5.1–5.5 (Session 7) |
| Orchestrator Planning Loop | ✅ Done | Manav — Tasks 4.3 (context_packet.py), 4.5 (planning_loop.py) |
| Vector / Embeddings | ✅ Done | Rahil — Tasks 7.1–7.5 |
| Evidence Scoring + Screenshots | ✅ Done | Rahil — Tasks 6.2–6.3 |
| Synthesis | ✅ Done | Rahil — Tasks 12.1–12.3 |
| Observability | ✅ Done | Bharath + Manav — Tasks 13.1–13.5 (logging, metrics, dashboards, tracing, DLQ) |
| Demo scripts | ✅ Done | Bharath — Tasks 14.1–14.5 |

### Run the UI Right Now (No Backend Required)

The War Room UI runs standalone with seeded mock data:

```bash
cd frontend
npm install  # already done; only needed on fresh clone
npm run dev
# Open http://localhost:5173
```

You will see the full war room: 6 agent tiles (4 active), 3 evidence cards across 3 themes, 7 timeline events, voice panel with mic toggle and waveform animation.

### Run the Backend

```bash
# ⚠️  If Homebrew Postgres is installed, stop it first — it conflicts on port 5432:
brew services stop postgresql@14   # adjust version if needed (check: brew services list)

cd backend
source venv/bin/activate   # or: python3 -m venv venv && source venv/bin/activate && pip install -e ".[dev]"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# GET http://localhost:8000/health → {"status": "ok"}
```

### Smoke-test the Nova Model Clients

Both model clients have self-contained smoke tests that hit the live Nova API:

```bash
# Requires NOVA_API_KEY in env (or .env file)
source backend/venv/bin/activate

# Test Nova 2 Lite (chat, plan_tasks, streaming)
NOVA_API_KEY=<your-key> python backend/models/lite_client.py

# Test Nova 2 Sonic (WebSocket voice, PCM audio output)
NOVA_API_KEY=<your-key> python backend/models/sonic_client.py
# Saves nova_sonic_smoke.wav for playback verification
```

---

## Team Task Files

Find your name below and open your task file first. Every task has full implementation notes, file paths, and coordination notes telling you what you need from other teammates.

| Name | Role | Task File |
|------|------|-----------|
| Bharath Gera | Team Lead / Project Setup & Demo | [team-tasks/bharath-gera.md](team-tasks/bharath-gera.md) |
| Manav Parikh | Cloud Infra & Mission Orchestrator | [team-tasks/manav-parikh.md](team-tasks/manav-parikh.md) |
| Rahil Singhi | Evidence Layer, Vectors & Synthesis | [team-tasks/rahil-singhi.md](team-tasks/rahil-singhi.md) |
| Chinmay Shringi | Voice Interface, Browser Agents & Planning | [team-tasks/chinmay-shringi.md](team-tasks/chinmay-shringi.md) |
| Sariya Rizwan | War Room UI & Frontend Streaming | [team-tasks/sariya-rizwan.md](team-tasks/sariya-rizwan.md) |

Full system task plan: [tasks.md](tasks.md)

---

## Prerequisites

Install these on your machine before anything else.

### Required

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Python | 3.12+ | [python.org/downloads](https://www.python.org/downloads/) or `brew install python@3.12` |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) or `brew install node` |
| Docker Desktop | Any recent | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| Git | Any recent | Pre-installed on macOS; `brew install git` if missing |
| AWS CLI v2 | 2.x | [docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |

### Optional but useful

| Tool | Use | Install |
|------|-----|---------|
| `uv` | Fast Python package manager | `pip install uv` |
| `httpie` | API testing from terminal | `brew install httpie` |
| `wscat` | WebSocket testing | `npm install -g wscat` |
| `redis-cli` | Inspect Redis locally | `brew install redis` |

---

## Step 1 — Clone the Repo

```bash
# Clone from the team's shared repository
git clone <repo-url>
cd VoiceAI

# Create your working branch
git checkout -b <your-name>/setup
```

---

## Step 2 — Nova API Key + AWS Access

Nova model inference uses **two separate auth systems** depending on the layer:

### 2a. Nova API Key (for model clients — already working)

The model clients (`models/lite_client.py`, `models/sonic_client.py`) use the **Nova API** at `api.nova.amazon.com` — an OpenAI-compatible REST + WebSocket interface. Auth is a Bearer token, not AWS IAM.

Get your key from [api.nova.amazon.com → API Keys](https://api.nova.amazon.com) and set it:

```bash
# In your .env file
NOVA_API_KEY=<your-key>
```

Verify it works:

```bash
curl -s -H "Authorization: Bearer $NOVA_API_KEY" \
  https://api.nova.amazon.com/v1/models | python3 -m json.tool
```

Nova API rate limits (free tier): Nova 2 Lite — 20 RPM / 500 RPD · Nova 2 Sonic — 5 concurrent / 20 sessions/day.
For higher limits, migrate to Amazon Bedrock (see 2b).

### 2b. AWS Credentials (for infra — Manav's tasks)

Required for deploying AWS infrastructure (ECS, Redis, Postgres, S3, OpenSearch). Get credentials from Bharath:

```bash
aws configure
# AWS Access Key ID: <from Bharath>
# AWS Secret Access Key: <from Bharath>
# Default region name: us-east-1
# Default output format: json
```

Verify:

```bash
aws sts get-caller-identity
```

### 2c. Bedrock model access (for production scale)

When migrating from Nova API to Bedrock for higher throughput, request access in the AWS console → Amazon Bedrock → Model access for:

- **Amazon Nova 2 Sonic** (voice model)
- **Amazon Nova 2 Lite** (orchestrator / planning model)
- **Amazon Nova Multimodal Embeddings** (evidence embeddings)

Use **us-east-1**. For now, the Nova API key is sufficient for all model work.

---

## Step 3 — Environment Variables

Copy the example env file and fill in the values you need:

```bash
cp .env.example .env
```

Open `.env` and fill in at minimum:

```env
NOVA_API_KEY=<your-key>   # required for all model clients (Lite + Sonic)
AWS_REGION=us-east-1
AWS_PROFILE=default
```

For **local development**, the Docker Compose services fill in most of the rest automatically (see Step 5). For **AWS-connected work**, get the remaining values from Bharath or from AWS SSM once Manav has deployed the infra stack.

See [docs/ENV.md](docs/ENV.md) for a description of every variable.

---

## Step 4 — Backend Setup (Python)

```bash
cd backend

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate       # macOS/Linux
# .\venv\Scripts\activate      # Windows

# Install all dependencies including dev tools
pip install -e ".[dev]"

# Verify
python -c "import fastapi, boto3, redis, openai, websockets; print('Backend deps OK')"
```

Run the smoke test to confirm everything imports correctly:

```bash
pytest tests/test_smoke.py -v
```

---

## Step 5 — Local Services (Docker Compose)

Starts Redis, Postgres, and MinIO (local S3) so you can run the backend without an AWS account for most tasks.

```bash
# From the repo root
make dev-up          # docker compose up -d (shorthand)

# Check all three are running
make dev-status      # docker compose ps
```

Expected output:

```
NAME         STATUS          PORTS
redis        Up              0.0.0.0:6379->6379/tcp
postgres     Up              0.0.0.0:5432->5432/tcp
minio        Up              0.0.0.0:9000->9000/tcp
```

**Postgres** connection: `postgresql://mc:mc@localhost:5432/missioncontrol`  
**Redis** connection: `redis://localhost:6379`  
**MinIO** (local S3) dashboard: [http://localhost:9001](http://localhost:9001) (login: `minioadmin` / `minioadmin`)

Update your `.env` for local dev:

```env
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql+asyncpg://mc:mc@localhost:5432/missioncontrol
S3_BUCKET_EVIDENCE=evidence
AWS_ENDPOINT_URL_S3=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
DEMO_MODE=true
```

---

## Step 6 — Frontend Setup (Node)

```bash
cd frontend

npm install   # installs react, zustand, tailwindcss, lucide-react, etc.

# Verify
npm run build
npm run test -- --run   # should pass
```

Create a frontend env file:

```bash
# frontend/.env.local  (gitignored)
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

> **Note:** The War Room UI already renders a fully-functional mock of the war room without any backend. Run `npm run dev` and open http://localhost:5173 to see it. The Zustand store is seeded with demo data (Sequoia mission, 6 agents, evidence cards, timeline events).

---

## Step 7 — Run the Backend

```bash
cd backend
source venv/bin/activate

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit [http://localhost:8000/health](http://localhost:8000/health) — should return:

```json
{"status": "ok"}
```

---

## Step 8 — Run the Frontend

In a separate terminal:

```bash
cd frontend
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173) — the War Room UI loads immediately with mock demo data. No backend required to see the full UI. The backend WebSocket endpoints are now live — `/ws/voice` (Voice Gateway) and `/ws/mission/{id}` (WS relay) — so with Docker Compose up and the backend running, the `useWebSocket` hook will connect automatically and replace mock data with live events. The War Room UI is fully connected to the live backend with real mission UUIDs from `POST /missions`.

---

## Step 9 — Run in Demo Mode (No AWS Required)

> ✅ **Status: Complete** — Both frontend (seeded mock data) and backend demo mode (`demo/seed_sequoia.py`, `demo/mock_evidence.json`) are fully implemented. Docker Compose required for backend demo.

If you do not have AWS credentials yet, or want to test UI and backend integration without calling Bedrock, set:

```bash
# In your .env
DEMO_MODE=true
```

With `DEMO_MODE=true`:
- Nova Sonic is stubbed with canned responses
- Browser agents emit mock evidence from `demo/mock_evidence.json`
- No real Bedrock calls are made
- Redis and Postgres are still required (Docker Compose handles these)

Start a demo mission:

```bash
python demo/seed_sequoia.py
```

For a quick frontend-only demo without Docker:

```bash
cd frontend && npm run dev
# Open http://localhost:5173 — full war room with seeded mock data
```

---

## Common Commands

### Backend

```bash
# Run backend dev server (from backend/ with venv active)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run all backend tests (smoke + integration — 43 tests)
pytest backend/tests/ -v

# Run smoke test only
pytest backend/tests/test_smoke.py -v

# Run integration tests only
pytest backend/tests/test_integration.py -v

# Lint and format check
ruff check backend/ agents/ --exclude backend/venv
black --check backend/ agents/

# Auto-fix formatting
black backend/ agents/
ruff check --fix backend/ agents/ --exclude backend/venv
```

### Frontend

```bash
# Dev server
npm run dev

# Type check (no emit)
npx tsc --noEmit

# Lint
npm run lint

# Run tests
npm run test

# Build for production
npm run build
```

### Docker

```bash
# Start local services
docker compose up -d

# Stop local services
docker compose down

# View logs
docker compose logs -f redis
docker compose logs -f postgres

# Reset Postgres (destructive — wipes all data)
docker compose down -v && docker compose up -d
```

### Redis inspection

```bash
# Connect to local Redis
redis-cli -h localhost -p 6379

# Watch all pub/sub events live
redis-cli -h localhost PSUBSCRIBE "mission:*"

# Check agent state
redis-cli HGETALL agent:agent_0
```

### API testing

```bash
# Create a mission
http POST localhost:8000/missions objective="Test mission" X-API-Key:changeme

# Get mission status
http GET localhost:8000/missions/<id> X-API-Key:changeme

# Get evidence for a mission
http GET localhost:8000/missions/<id>/evidence X-API-Key:changeme

# Reset demo state
http POST localhost:8000/demo/reset X-API-Key:changeme

# Connect to mission WebSocket (requires wscat)
wscat -c "ws://localhost:8000/ws/mission/<id>"
```

---

## Repository Structure

All files marked `✅` exist and are functional.

```
VoiceAI/
├── tasks.md                    ✅ Full system engineering plan (with progress tracker)
├── CLAUDE.md                   ✅ This file
├── .env.example                ✅ 18 placeholder env vars (incl. NOVA_API_KEY, AWS_BEARER_TOKEN_BEDROCK)
├── docker-compose.yml          ✅ Redis 7 + Postgres 16 + MinIO + bucket init
├── Makefile                    ✅ dev-up/down/logs/reset/status + backend/frontend helpers
│
├── team-tasks/                 ✅ All task files updated with current status
│   ├── bharath-gera.md         ✅ 16/16 tasks done (all complete — Session 8)
│   ├── manav-parikh.md         ✅ 11/14 tasks done (remaining 3 are CDK deploy — needs AWS account)
│   ├── rahil-singhi.md         ✅ 15/15 tasks done (all complete — Session 8)
│   ├── chinmay-shringi.md      ✅ 16/16 tasks done (all complete — Session 7)
│   └── sariya-rizwan.md        ✅ 11/11 tasks done (all complete — Session 7)
│
├── .github/
│   └── workflows/
│       └── ci.yml              ✅ 4 parallel jobs — green
│
├── backend/
│   ├── main.py                 ✅ FastAPI app + lifespan (asyncpg pool + Redis) + CORS
│   ├── config.py               ✅ Pydantic Settings class (reads root .env)
│   ├── deps.py                 ✅ Shared FastAPI dependencies (get_db, get_redis)
│   ├── pyproject.toml          ✅ All Python deps pinned
│   ├── logging_config.py       ✅ Done (Bharath Task 13.1)
│   ├── missions/               ✅ Done (Bharath Tasks 4.1–4.2)
│   │   ├── __init__.py         ✅
│   │   ├── schemas.py          ✅ MissionCreate, MissionRecord, MissionStatus
│   │   ├── repository.py       ✅ create_mission, get_mission, update_mission_status
│   │   └── router.py           ✅ POST /missions, GET /missions/{id}, PATCH /missions/{id}
│   ├── evidence/               ✅ Done (Rahil Tasks 6.1 + 6.4)
│   │   ├── __init__.py         ✅
│   │   ├── schemas.py          ✅ EvidenceIngest, EvidenceRecord
│   │   ├── repository.py       ✅ create_evidence, get_evidence_by_mission
│   │   └── router.py           ✅ POST /evidence, GET /missions/{id}/evidence
│   ├── gateway/                ✅ Done (Chinmay Task 3.3)
│   │   ├── __init__.py         ✅
│   │   └── voice_gateway.py    ✅ /ws/voice — Nova Sonic bridge, 5 tool handlers
│   ├── streaming/              ✅ Done (Tasks 9.1 + 9.2)
│   │   ├── __init__.py         ✅
│   │   ├── channels.py         ✅ channel name helpers + publish()
│   │   └── ws_relay.py         ✅ /ws/mission/{id} — Redis pub/sub → browser WS
│   ├── models/                 ✅ Moved from repo root (Session 5 fix)
│   │   ├── __init__.py         ✅ Package init — exports all clients
│   │   ├── sonic_client.py     ✅ Nova 2 Sonic real-time WebSocket client (Task 3.1)
│   │   ├── sonic_tools.py      ✅ 5 tool schemas — Nova Realtime + Bedrock formats (Task 3.2)
│   │   ├── lite_client.py      ✅ Nova 2 Lite chat/plan/stream client (Task 4.4)
│   │   └── embedding_client.py ✅ Done (Rahil Task 7.1)
│   ├── orchestrator/           ✅ Done (Manav Tasks 4.3, 4.5)
│   │   ├── __init__.py         ✅
│   │   ├── context_packet.py   ✅ Context assembly for planning loop (Task 4.3)
│   │   └── planning_loop.py    ✅ Orchestrator planning loop (Task 4.5)
│   ├── synthesis/              ✅ Done (Rahil Tasks 12.1–12.3)
│   └── tests/
│       ├── __init__.py         ✅
│       ├── test_smoke.py       ✅ async health check — passing
│       └── test_integration.py ✅ 43 tests — mission CRUD, state machine, evidence, WS relay
│
├── agents/
│   └── prompts/                ✅ directory exists (Chinmay to populate Task 5.3)
│
├── frontend/
│   ├── package.json            ✅ All deps (react, zustand, tanstack, tailwindcss, lucide-react…)
│   ├── tsconfig.json           ✅
│   ├── vite.config.ts          ✅ vitest jsdom config
│   ├── tailwind.config.ts      ✅ war room color palette
│   ├── postcss.config.js       ✅
│   ├── eslint.config.js        ✅ ESLint 9 flat config
│   ├── index.html              ✅
│   └── src/
│       ├── main.tsx            ✅
│       ├── App.tsx             ✅ renders WarRoomLayout
│       ├── App.test.tsx        ✅ Vitest smoke test — passing
│       ├── index.css           ✅ Tailwind base + war room styles
│       ├── types/
│       │   └── api.ts          ✅ TypeScript interfaces (all schemas)
│       ├── store/
│       │   └── index.ts        ✅ Zustand store (seeded with Sequoia demo data)
│       ├── hooks/
│       │   └── useWebSocket.ts ✅ WS hook with exponential-backoff reconnect
│       └── components/
│           ├── layout/
│           │   ├── WarRoomLayout.tsx  ✅ CSS grid, 100vh, 4 regions
│           │   └── Header.tsx         ✅ brand, mission badge, connection dot
│           ├── StatusBadge.tsx        ✅ IDLE/ASSIGNED/BROWSING/REPORTING pills
│           ├── AgentTile.tsx          ✅ card + scanning animation
│           ├── AgentGrid.tsx          ✅ 2-col grid of 6 tiles
│           ├── EvidenceCard.tsx       ✅ confidence meter, theme pill, source
│           ├── EvidenceBoard.tsx      ✅ scrollable + theme filter
│           ├── MissionTimeline.tsx    ✅ 7 event types + lucide icons
│           └── VoicePanel.tsx         ✅ mic toggle, 60fps waveform, transcript
│
├── infra/
│   ├── cdk/                    ✅ Done — CDK stacks for all AWS resources
│   └── init.sql                ✅ missions + tasks + evidence tables, enums, indexes
│
├── demo/                       ✅ Done (Bharath Tasks 14.1–14.5)
│
└── docs/
    ├── ENV.md                  ✅ Full variable reference
    ├── EVENTS.md               ✅ Done — full channel + payload spec (Task 9.1)
    ├── VOICE_FORMAT.md         ✅ Done (Chinmay Task 3.4)
    ├── IAM.md                  ✅ Done (Bharath Task 2.6)
    ├── LOGGING.md              ✅ Done (Bharath Task 13.1)
    ├── DEMO.md                 ✅ Done (Bharath Task 14.1)
    └── FRONTEND_STREAMING.md   ✅ Done (Sariya Task 9.4)
```

---

## Branch and Commit Conventions

```bash
# Branch naming
git checkout -b <name>/<feature>
# e.g. git checkout -b chinmay/voice-gateway
# e.g. git checkout -b rahil/evidence-layer
# e.g. git checkout -b sariya/agent-grid

# Commit format
git commit -m "<type>(<scope>): <short description>"
# Types: feat, fix, refactor, test, docs, chore
# e.g. feat(evidence): add POST /evidence ingest endpoint
# e.g. fix(gateway): handle WebSocket disconnect cleanly
# e.g. docs(voice): add VOICE_FORMAT.md for audio spec

# Before pushing, run
ruff check . && black --check . && pytest backend/tests/ -x
```

---

## Working with Claude (AI Pair Programming)

This project uses Claude as an AI coding assistant inside Cursor. A few guidelines for effective prompts:

- **Be specific about the file path**: "Implement `backend/evidence/scoring.py` — the `compute_confidence` function from Task 6.3 in my task file." Claude will read the task file for context.
- **Reference the schema**: "Create the `EvidenceIngest` Pydantic model in `backend/evidence/schemas.py` matching the EvidenceRecord schema in `tasks.md`."
- **Describe what you already have**: "I've finished Task 6.1 (evidence schema). Now help me implement Task 6.2 — the S3 screenshot upload in `backend/evidence/screenshot.py`."
- **Ask Claude to read first**: "Read `backend/evidence/repository.py` and then add the `update_evidence_novelty` function."
- **Test immediately**: After each task, ask "Write a pytest test for this function using mock asyncpg."

---

## Coordination and Integration Points

These are the cross-team touchpoints most likely to cause merge conflicts or blocking dependencies. Flag in the team chat when you complete any of these.

| Event | Who completes it | Who is unblocked |
|-------|-----------------|------------------|
| ~~`POST /missions` API live (`localhost:8000/missions`)~~ | ~~Bharath~~ ✅ **Done** | Chinmay (voice gateway tool execution ✅), Rahil (demo), Sariya (API calls from UI) |
| ~~`POST /evidence` API live~~ | ~~Rahil~~ ✅ **Done** | Chinmay (agents emit to this endpoint) |
| ~~Redis channels defined (`docs/EVENTS.md`)~~ | ~~Bharath~~ ✅ **Done** | Sariya (WS relay ✅), Chinmay (AGENT_UPDATE events) |
| ~~Voice Gateway WebSocket live (`/ws/voice`)~~ | ~~Chinmay~~ ✅ **Done** | Sariya (VoicePanel can now connect) |
| ~~Mission WebSocket relay live (`/ws/mission/{id}`)~~ | ~~Bharath~~ ✅ **Done** | Full event pipe confirmed (574 ms `POST /evidence` → browser) |
| ~~Connect War Room UI to live backend~~ | ~~Sariya~~ ✅ **Done** | Real mission UUID from `POST /missions` integrated |
| ~~`models/lite_client.py` exists~~ | ~~Manav~~ ✅ **Done** | Chinmay (task decomposition, Task 10.1), Rahil (theme labeller, Task 7.4) |
| ~~`models/sonic_client.py` + `sonic_tools.py` exist~~ | ~~Chinmay~~ ✅ **Done** | Voice Gateway built ✅ |
| ~~`models/embedding_client.py` exists + dimension constant exported~~ | ~~Rahil~~ ✅ **Done** | Manav (OpenSearch index dimension, Task 2.5) |
| ~~Docker Compose up (`docker-compose.yml` created — Task 2.7)~~ | ~~Bharath~~ ✅ **Done** | Everyone can now run Redis + Postgres + MinIO locally |

**Communication**: when you start a task that another person depends on, drop a note in the team chat with the expected interface (endpoint path, function signature, or message format) so they can build against it while you implement.

---

## Troubleshooting

### `pip install` fails with Python version error

Make sure you are using Python 3.12+:

```bash
python3 --version
# If wrong version:
brew install python@3.12
python3.12 -m venv venv
```

### Docker Compose containers not starting

```bash
docker compose down -v   # remove volumes
docker compose up -d     # fresh start
docker compose logs      # read errors
```

### Postgres connection refused

The Postgres container takes 5–10 s to be ready on first boot. Wait and retry:

```bash
docker compose exec postgres psql -U mc -d missioncontrol -c "SELECT 1"
```

### `role "mc" does not exist` when connecting via asyncpg

A local Homebrew Postgres is squatting on port 5432, intercepting connections before Docker's container gets them. Fix:

```bash
# Find the conflicting service
brew services list | grep postgres
lsof -i :5432

# Stop it (restart later with 'start')
brew services stop postgresql@14   # adjust version number

# Verify Docker's Postgres is now reachable
python3 -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('postgresql://mc:mc@localhost:5432/missioncontrol'))"
```

### Bedrock `AccessDeniedException`

You do not have model access yet. Check the Bedrock console → Model access page for your region (`us-east-1`). If you see "Available to request", click Request access.

### `REDIS_URL` connection error

Check Docker Compose is running: `docker compose ps`. Redis should show `Up`. If using AWS ElastiCache, check security group allows your IP or Fargate SG.

### Frontend `VITE_WS_URL` undefined

Make sure you have a `.env.local` file in `frontend/` (not `.env`). Vite uses `.env.local` for local overrides.

### `422 Unprocessable Entity` on `POST /evidence`

The request body does not match `EvidenceIngest` schema. Check required fields: `mission_id`, `agent_id`, `claim`, `summary`, `source_url`, `snippet`. Run `http POST localhost:8000/evidence --verbose` to see the validation error detail.

---

*Last updated: March 2026 — Session 8. Questions? Ask Bharath or drop a message in the team chat.*

**Quick status:** All tasks complete. **68/68 tasks done (100%).** Full E2E pipeline live: `POST /missions` → Nova Lite → Postgres ✅. `PATCH /missions/{id}` enforces valid state transitions ✅. `POST /evidence` → Redis `EVIDENCE_FOUND` → browser via `useWebSocket` ✅. `/ws/voice` multi-turn with interrupt handling ✅. Browser agents (5.1–5.5) ✅. Orchestrator planning loop (4.3, 4.5) ✅. Vector/embeddings (7.1–7.5) ✅. Evidence scoring + screenshots (6.2–6.3) ✅. Synthesis (12.1–12.3) ✅. AWS CDK infra (2.1–2.7) ✅. Observability — logging, metrics, dashboards, tracing, DLQ (13.1–13.5) ✅. Demo scripts (14.1–14.5) ✅. War Room UI fully connected to live backend ✅. Only remaining work: CDK deploy to AWS account (Manav 3/14 tasks — needs AWS account access). See `tasks.md` → Implementation Progress.
