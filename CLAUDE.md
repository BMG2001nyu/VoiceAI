# Mission Control (Dispatch) — Getting Started Guide

This file is the single source of truth for getting your local environment running and starting work on your assigned tasks.

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

This starts Redis, Postgres, and MinIO (local S3) so you can run the backend without an AWS account for most tasks.

```bash
# From the repo root
docker compose up -d

# Check all three are running
docker compose ps
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

npm install

# Verify
npm run build
```

Copy the frontend env:

```bash
cp .env.example .env.local
```

`.env.local`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

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

Visit [http://localhost:5173](http://localhost:5173) — the War Room UI will load.

---

## Step 9 — Run in Demo Mode (No AWS Required)

If you do not have AWS credentials yet, or want to test UI and backend integration without calling Bedrock:

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

---

## Common Commands

### Backend

```bash
# Run backend dev server
uvicorn backend.main:app --reload

# Run all backend tests
pytest backend/tests/ -v

# Run specific test file
pytest backend/tests/test_missions.py -v

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

```
VoiceAI/
├── tasks.md                    # Full system engineering plan
├── CLAUDE.md                   # This file
├── .env.example                # Template for environment variables
├── docker-compose.yml          # Local dev services (Redis, Postgres, MinIO)
│
├── team-tasks/                 # Individual task files — read yours first
│   ├── bharath-gera.md
│   ├── manav-parikh.md
│   ├── rahil-singhi.md
│   ├── chinmay-shringi.md
│   └── sariya-rizwan.md
│
├── backend/                    # FastAPI backend
│   ├── main.py                 # App entrypoint
│   ├── config.py               # Settings (Pydantic)
│   ├── logging_config.py       # Structlog setup
│   ├── missions/               # Mission state machine + CRUD
│   ├── orchestrator/           # Planning loop, context builder
│   ├── evidence/               # Evidence ingest, scoring, clustering
│   ├── gateway/                # Voice gateway, WebSocket relay
│   ├── synthesis/              # Briefing generation
│   ├── routers/                # FastAPI routers
│   └── tests/                  # Pytest test suite
│
├── agents/                     # Browser agent system
│   ├── browser_session.py      # Nova Act session manager
│   ├── pool.py                 # Agent pool
│   ├── lifecycle.py            # State + heartbeat
│   ├── evidence_emitter.py     # Evidence extraction + POST
│   ├── command_channel.py      # Redis command consumer
│   └── prompts/                # Per-agent-type system prompts
│
├── models/                     # Model wrappers
│   ├── sonic_client.py         # Nova Sonic streaming
│   ├── sonic_tools.py          # Tool schema definitions
│   ├── lite_client.py          # Nova Lite (orchestrator)
│   └── embedding_client.py     # Nova Multimodal Embeddings
│
├── frontend/                   # React + Vite War Room UI
│   ├── src/
│   │   ├── App.tsx
│   │   ├── store/              # Zustand state
│   │   ├── hooks/              # WebSocket, throttle
│   │   ├── components/         # UI components
│   │   └── types/              # TypeScript API types
│   └── vite.config.ts
│
├── infra/                      # AWS CDK or Terraform
│   ├── cdk/                    # CDK stacks
│   └── init.sql                # Postgres schema
│
├── demo/                       # Demo scenario scripts
│   ├── seed_sequoia.py         # Start the Sequoia demo mission
│   ├── mock_evidence.json      # Offline evidence dataset
│   ├── run_demo.sh             # One-command demo launcher
│   └── load_test.py            # 10-mission parallel load test
│
└── docs/                       # Technical documentation
    ├── ENV.md                  # Environment variable reference
    ├── EVENTS.md               # Redis pub/sub event formats
    ├── VOICE_FORMAT.md         # Audio format for voice WebSocket
    ├── IAM.md                  # AWS IAM permissions reference
    ├── LOGGING.md              # Structured log format
    ├── DEMO.md                 # Demo operator guide
    ├── FRONTEND_STREAMING.md   # WS batching + backpressure
    └── architecture.png        # System diagram
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
| Docker Compose up | Bharath | Everyone |

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

*Last updated: March 2026. Questions? Ask Bharath or drop a message in the team chat.*
