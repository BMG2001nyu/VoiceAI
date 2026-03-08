# Mission Control (Dispatch) — Getting Started Guide

This file is the single source of truth for getting your local environment running and starting work on your assigned tasks.

---

## Current Implementation Status

**Last updated:** March 2026 — Session 2

### What Is Done

| Area | Status | Key Files |
|------|--------|-----------|
| Monorepo scaffold | ✅ Done | All dirs, `.gitignore`, `README.md` |
| Backend deps | ✅ Done | `backend/pyproject.toml` (all 10 runtime deps + dev extras) |
| Frontend deps | ✅ Done | `frontend/package.json`, `package-lock.json`, `tsconfig.json` |
| Env config | ✅ Done | `.env.example`, `docs/ENV.md`, `backend/config.py` |
| CI pipeline | ✅ Done | `.github/workflows/ci.yml` (4 parallel jobs, green) |
| Backend health endpoint | ✅ Done | `GET /health → {"status": "ok"}` in `backend/main.py` |
| Backend smoke test | ✅ Done | `backend/tests/test_smoke.py` — passing |
| War Room UI | ✅ Done | Full dark war room layout, all panels rendered with mock data |
| TypeScript types | ✅ Done | `frontend/src/types/api.ts` — all schemas (Mission, Agent, Evidence, Timeline) |
| Zustand store | ✅ Done | `frontend/src/store/index.ts` — seeded with Sequoia demo mission |
| WebSocket hook | 🔄 Partial | `frontend/src/hooks/useWebSocket.ts` — reconnection logic ready, needs live backend |
| AWS Infra | ⏳ Pending | Manav — Tasks 2.1–2.7 |
| Voice Gateway | ⏳ Pending | Chinmay — Tasks 3.1–3.5 |
| Mission Orchestrator | ⏳ Pending | Manav — Tasks 4.1–4.5 |
| Browser Agents | ⏳ Pending | Chinmay — Tasks 5.1–5.5 |
| Evidence Layer | ⏳ Pending | Rahil — Tasks 6.1–6.4 |
| Vector / Embeddings | ⏳ Pending | Rahil — Tasks 7.1–7.5 |
| WS Streaming (backend) | ⏳ Pending | Manav + Sariya — Tasks 9.1–9.4 |
| Synthesis | ⏳ Pending | Rahil — Tasks 12.1–12.3 |
| Observability | ⏳ Pending | Bharath + Manav — Tasks 13.1–13.5 |
| Demo scripts | ⏳ Pending | Bharath — Tasks 14.1–14.5 |

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
cd backend
source venv/bin/activate   # or: python3 -m venv venv && source venv/bin/activate && pip install -e ".[dev]"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# GET http://localhost:8000/health → {"status": "ok"}
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

## Step 2 — AWS Access

You need an AWS account with Bedrock model access before you can run anything that touches Nova models.

### 2a. Configure AWS credentials

```bash
# If the team shares a single AWS account, get your access key from Bharath
aws configure
# AWS Access Key ID: <from Bharath>
# AWS Secret Access Key: <from Bharath>
# Default region name: us-east-1
# Default output format: json
```

Verify it works:

```bash
aws sts get-caller-identity
```

You should see your account ID and user ARN printed. If you see an error, your credentials are not set up correctly — ask Bharath.

### 2b. Request Bedrock model access

In the AWS console → Amazon Bedrock → Model access → request access for:

- **Amazon Nova 2 Sonic** (voice model)
- **Amazon Nova 2 Lite** (orchestrator / planning model)
- **Amazon Nova Multimodal Embeddings** (evidence embeddings)

Access is granted per-region. Use **us-east-1** unless Bharath specifies otherwise. Model access can take a few minutes to propagate.

Verify access from terminal:

```bash
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[?contains(modelId, 'nova')].modelId"
```

---

## Step 3 — Environment Variables

Copy the example env file and fill in the values you need:

```bash
cp .env.example .env
```

Open `.env` and fill in at minimum:

```env
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
python -c "import fastapi, boto3, redis; print('Backend deps OK')"
```

Run the smoke test to confirm everything imports correctly:

```bash
pytest tests/test_smoke.py -v
```

---

## Step 5 — Local Services (Docker Compose)

> ⚠️ **Status: Pending** — `docker-compose.yml` has not been created yet (Bharath Task 2.7, blocked on Manav's schema). Check `team-tasks/bharath-gera.md` for current status before attempting this step. Skip to Step 6 if you only need the frontend UI.

When available, this will start Redis, Postgres, and MinIO (local S3) so you can run the backend without an AWS account for most tasks.

```bash
# From the repo root
docker compose up -d

# Check all three are running
docker compose ps
```

Expected output once the file exists:

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

Visit [http://localhost:5173](http://localhost:5173) — the War Room UI loads immediately with mock demo data. No backend required to see the full UI. When the backend WebSocket endpoints are live (Chinmay's `/ws/voice` and Manav's `/ws/mission/{id}`), the `useWebSocket` hook will connect automatically and replace the mock data with live events.

---

## Step 9 — Run in Demo Mode (No AWS Required)

> ⚠️ **Status: Partial** — The frontend runs in demo mode automatically right now (seeded with mock data, no backend needed). The full backend demo mode (`demo/seed_sequoia.py`, `demo/mock_evidence.json`) is pending Bharath Tasks 14.1–14.2 and requires Docker Compose to be live.

If you do not have AWS credentials yet, or want to test UI and backend integration without calling Bedrock, set:

```bash
# In your .env
DEMO_MODE=true
```

With `DEMO_MODE=true` (once backend demo is implemented):
- Nova Sonic is stubbed with canned responses
- Browser agents emit mock evidence from `demo/mock_evidence.json`
- No real Bedrock calls are made
- Redis and Postgres are still required (Docker Compose handles these)

Start a demo mission (once `demo/` scripts exist):

```bash
python demo/seed_sequoia.py
```

**Right now**, the fastest way to see a working demo is:

```bash
cd frontend && npm run dev
# Open http://localhost:5173 — full war room with live mock data
```

---

## Common Commands

### Backend

```bash
# Run backend dev server (from backend/ with venv active)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run all backend tests (currently: smoke test only)
pytest backend/tests/ -v

# Run smoke test specifically
pytest backend/tests/test_smoke.py -v

# Lint and format check
ruff check backend/ models/ agents/
black --check backend/ models/ agents/

# Auto-fix formatting
black backend/ models/ agents/
ruff check --fix backend/ models/ agents/
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

Files marked `✅` exist and are functional. Files marked `⏳` are planned but not yet created.

```
VoiceAI/
├── tasks.md                    ✅ Full system engineering plan (with progress tracker)
├── CLAUDE.md                   ✅ This file
├── .env.example                ✅ 13 placeholder env vars
├── docker-compose.yml          ⏳ Pending (Bharath Task 2.7)
│
├── team-tasks/                 ✅ All task files updated with current status
│   ├── bharath-gera.md         ✅ 4/12 tasks done
│   ├── manav-parikh.md         ✅ 0/14 tasks (all pending)
│   ├── rahil-singhi.md         ✅ 0/15 tasks (all pending)
│   ├── chinmay-shringi.md      ✅ 0/16 tasks (all pending)
│   └── sariya-rizwan.md        ✅ 7/11 tasks done
│
├── .github/
│   └── workflows/
│       └── ci.yml              ✅ 4 parallel jobs — green
│
├── backend/
│   ├── main.py                 ✅ FastAPI app + GET /health
│   ├── config.py               ✅ Pydantic Settings class (reads .env)
│   ├── pyproject.toml          ✅ All Python deps pinned
│   ├── logging_config.py       ⏳ Pending (Bharath Task 13.1)
│   ├── missions/               ⏳ Pending (Manav Tasks 4.1–4.2)
│   ├── orchestrator/           ⏳ Pending (Manav Tasks 4.3–4.5)
│   ├── evidence/               ⏳ Pending (Rahil Tasks 6.1–6.4)
│   ├── gateway/                ⏳ Pending (Chinmay Task 3.3)
│   ├── synthesis/              ⏳ Pending (Rahil Tasks 12.1–12.3)
│   ├── routers/                ⏳ Pending
│   ├── streaming/              ⏳ Pending (Manav Task 9.1)
│   └── tests/
│       ├── __init__.py         ✅
│       └── test_smoke.py       ✅ async health check — passing
│
├── agents/
│   └── prompts/                ✅ directory exists (Chinmay to populate Task 5.3)
│
├── models/                     ✅ directory exists
│   ├── sonic_client.py         ⏳ Pending (Chinmay Task 3.1)
│   ├── sonic_tools.py          ⏳ Pending (Chinmay Task 3.2)
│   ├── lite_client.py          ⏳ Pending (Manav Task 4.4)
│   └── embedding_client.py     ⏳ Pending (Rahil Task 7.1)
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
│   ├── cdk/                    ✅ directory exists (Manav to populate)
│   └── init.sql                ⏳ Pending (Bharath Task 2.7)
│
├── demo/                       ⏳ Pending (Bharath Tasks 14.x)
│
└── docs/
    ├── ENV.md                  ✅ Full variable reference
    ├── EVENTS.md               ⏳ Pending (Manav Task 9.1)
    ├── VOICE_FORMAT.md         ⏳ Pending (Chinmay Task 3.4)
    ├── IAM.md                  ⏳ Pending (Bharath Task 2.6)
    ├── LOGGING.md              ⏳ Pending (Bharath Task 13.1)
    ├── DEMO.md                 ⏳ Pending (Bharath Task 14.1)
    └── FRONTEND_STREAMING.md   ⏳ Pending (Sariya Task 9.4)
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
| `POST /missions` API live (`localhost:8000/missions`) | Manav | Chinmay (voice gateway tool execution), Rahil (demo), Sariya (API calls from UI) |
| `POST /evidence` API live | Rahil | Chinmay (agents emit to this endpoint) |
| Redis channels defined (`docs/EVENTS.md`) | Manav | Sariya (WebSocket relay), Chinmay (AGENT_UPDATE events) |
| Voice Gateway WebSocket live (`/ws/voice`) | Chinmay | Sariya (VoicePanel connects) |
| Mission WebSocket relay live (`/ws/mission/{id}`) | Sariya | Sariya can test live evidence streaming |
| `models/lite_client.py` exists | Manav (creates it in Task 4.4) | Chinmay (task decomposition, Task 10.1), Rahil (theme labeller, Task 7.4) |
| `models/embedding_client.py` exists + dimension constant exported | Rahil | Manav (OpenSearch index dimension, Task 2.5) |
| Docker Compose up (`docker-compose.yml` created — Task 2.7) | Bharath | Everyone needing local Redis/Postgres |

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

### Bedrock `AccessDeniedException`

You do not have model access yet. Check the Bedrock console → Model access page for your region (`us-east-1`). If you see "Available to request", click Request access.

### `REDIS_URL` connection error

Check Docker Compose is running: `docker compose ps`. Redis should show `Up`. If using AWS ElastiCache, check security group allows your IP or Fargate SG.

### Frontend `VITE_WS_URL` undefined

Make sure you have a `.env.local` file in `frontend/` (not `.env`). Vite uses `.env.local` for local overrides.

### `422 Unprocessable Entity` on `POST /evidence`

The request body does not match `EvidenceIngest` schema. Check required fields: `mission_id`, `agent_id`, `claim`, `summary`, `source_url`, `snippet`. Run `http POST localhost:8000/evidence --verbose` to see the validation error detail.

---

*Last updated: March 2026 — Session 2. Questions? Ask Bharath or drop a message in the team chat.*

**Quick status:** Phase 1 complete (scaffold + CI + UI). Waiting on Manav (AWS infra), Chinmay (voice gateway + agent prompts), and Rahil (embedding client dimension) to unblock Phases 2–6. See `tasks.md` → Implementation Progress for the full tracker.
