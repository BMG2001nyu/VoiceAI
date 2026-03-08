# Mission Control — Tasks for Bharath Gera

**Role:** Team Lead / Project Architect  
**GitHub:** [bharathgera](https://github.com/BharathGera)  
**LinkedIn:** [bharathgera](https://www.linkedin.com/in/bharathgera/)

---

## Implementation Status

**Last updated:** March 2026

| Task | Status | Notes |
|------|--------|-------|
| 1.1 Monorepo Scaffold | ✅ Done | All dirs, `.gitignore`, `README.md` |
| 1.2 Dependency Manifests | ✅ Done | `backend/pyproject.toml`, `frontend/package.json`, `package-lock.json` |
| 1.3 Environment Config | ✅ Done | `.env.example` (13 vars), `docs/ENV.md`, `backend/config.py` (Pydantic Settings) |
| 1.4 CI Skeleton | ✅ Done | `.github/workflows/ci.yml`, `/health` endpoint, smoke tests passing |
| 2.6 IAM + Secrets | ⏳ Pending | Needs Manav's AWS stack outputs (2.2–2.5) |
| 2.7 Docker Compose | ⏳ Pending | Needs Manav's schema finalization |
| 13.1 Structured Logging | ⏳ Pending | Needs Phase 4–6 in place |
| 14.1 Demo Seed Script | ⏳ Pending | Needs Phase 4, 5, 10 |
| 14.2 Mock Mode | ⏳ Pending | Needs Phase 5, 6, 8 |
| 14.3 Demo Reset Endpoint | ⏳ Pending | Needs Phase 4, 6, 9 |
| 14.4 Architecture Diagram | ⏳ Pending | Can be done anytime |
| 14.5 Load Test Script | ⏳ Pending | Needs Phase 4, 12 |

### Phase 1 — Complete ✅

All foundation tasks are done and verified. CI runs green. The backend serves `GET /health → {"status": "ok"}`. Frontend builds and tests pass. Both `pip install -e ".[dev]"` and `npm install` work on a clean checkout.

### Blocked On / Next Steps

- **2.7 Docker Compose** — blocked on Manav confirming the `infra/init.sql` schema matches his RDS schema. Once confirmed: create `docker-compose.yml` and `infra/init.sql`.
- **13.1 Structured Logging** — add `backend/logging_config.py` once other services are being built so the context vars (`mission_id`, `agent_id`) have callers.
- **14.x Demo tasks** — all require multiple other phases to be complete. Return to these once Phases 4–10 are done.
- **2.6 IAM** — once Manav has ARNs from CDK outputs, create `docs/IAM.md` and the least-privilege policies.

---

## Why These Tasks

As team lead you own the skeleton that every other engineer builds on top of, the secrets and IAM baseline that keeps AWS costs and security clean, the observability logging standard that every service follows, and the full demo scenario that the team presents. You set up the repository, unblock everyone in the first 24 hours, and close out the project with a polished, repeatable demo.

---

## Task Summary

| Task | Phase | Description | Depends On | Status |
|------|-------|-------------|------------|--------|
| 1.1 | Project Init | Monorepo scaffold | — | ✅ Done |
| 1.2 | Project Init | Dependency manifests | 1.1 | ✅ Done |
| 1.3 | Project Init | Environment config strategy | 1.1 | ✅ Done |
| 1.4 | Project Init | CI skeleton | 1.2 | ✅ Done |
| 2.6 | Infrastructure | IAM roles + Secrets Manager | 2.2–2.5 | ⏳ Pending |
| 2.7 | Infrastructure | Local dev Docker Compose | 1.3, 2.2–2.4 | ⏳ Pending |
| 13.1 | Observability | Structured JSON logging standard | Phase 4, 5, 6 | ⏳ Pending |
| 14.1 | Demo | Seeded demo mission script | Phase 4, 5, 10 | ⏳ Pending |
| 14.2 | Demo | Mock mode for offline demo | 5.4, 6.1, 8.x | ⏳ Pending |
| 14.3 | Demo | Demo reset endpoint | Phase 4, 6, 9 | ⏳ Pending |
| 14.4 | Demo | Architecture diagram export | — | ⏳ Pending |
| 14.5 | Demo | Load test script | Phase 4, 12 | ⏳ Pending |

**Total: 12 tasks — 4 Done, 8 Pending**

---

## Coordination Map

| You need from | What |
|---------------|------|
| **Manav** | AWS stack outputs (Redis URL, DB URL, OpenSearch endpoint, S3 bucket name) before 2.6 and 2.7 |
| **All** | Services must follow the JSON log format defined in 13.1 |
| **Chinmay** | Voice Gateway and Orchestrator running for demo scenario (14.1) |
| **Rahil** | Evidence layer and vector endpoints working for demo (14.1) |
| **Sariya** | War Room UI deployable for demo (14.1, 14.2) |

---

## Full Task Details

---

### Task 1.1 — Monorepo Scaffold

**Description:** Create the root directory structure and placeholder files for `frontend/`, `backend/`, `agents/`, `models/`, `infra/`. No business logic yet — just the skeleton that gives every team member a place to land.

**Technical implementation notes:**
- Create the following directories at repo root: `frontend/`, `backend/`, `agents/agents/prompts/`, `models/`, `infra/cdk/` (or `infra/terraform/`), `docs/`.
- Add `.gitkeep` to empty dirs so they appear in git.
- Root files: `README.md` (project overview, links to `tasks.md` and `team-tasks/`), `.gitignore` (Python bytecode, `.env`, `venv/`, `node_modules/`, `.DS_Store`, CDK `cdk.out/`).
- `README.md` must document the directory layout, prerequisites (Python 3.12+, Node 20+, AWS CLI, Docker), and how to run locally.

**Dependencies:** None — this is the first task and unblocks everyone.

**Expected output:** All five directories exist; `git status` shows a clean structure; README visible in GitHub.

**Subtasks:**
- 1.1.1 Create directories and `.gitkeep` files.
- 1.1.2 Write root `.gitignore` covering Python, Node, env, CDK, and IDE files.
- 1.1.3 Write `README.md` with architecture one-liner, prerequisites table, and `Quick Start` section.

---

### Task 1.2 — Dependency Manifests

**Description:** Define Python and Node dependency manifests so every engineer can install a consistent environment from day one.

**Technical implementation notes:**
- **Python** (`backend/pyproject.toml`): use `[project]` table with `requires-python = ">=3.12"`. Pin major.minor. Include: `fastapi>=0.111`, `uvicorn[standard]>=0.29`, `pydantic>=2.6`, `httpx>=0.27`, `boto3>=1.34`, `redis[hiredis]>=5.0`, `asyncpg>=0.29`, `sqlalchemy[asyncio]>=2.0`, `python-dotenv>=1.0`, `structlog>=24.1`. Add `[project.optional-dependencies]` with `dev = ["pytest", "pytest-asyncio", "ruff", "black"]`.
- **Node** (`frontend/package.json`): `"type": "module"`, scripts `dev`, `build`, `preview`, `test`, `lint`. Dependencies: `react`, `react-dom`, `zustand`, `@tanstack/react-query`. DevDeps: `vite`, `typescript`, `@types/react`, `@types/react-dom`, `eslint`, `vitest`, `@vitejs/plugin-react`.
- Pin all dep versions with exact ranges; commit `frontend/package-lock.json`.

**Dependencies:** Task 1.1.

**Expected output:** `pip install -e ".[dev]"` and `npm install` succeed on a fresh checkout; no unresolved deps.

---

### Task 1.3 — Environment Config Strategy

**Description:** Document and scaffold all environment variables. Provide `.env.example` so any engineer can copy it, fill in values, and have a working local environment without guessing what is needed.

**Technical implementation notes:**
- File: `.env.example` at repo root. Content (placeholders only, no real values):
  ```
  # AWS
  AWS_REGION=us-east-1
  AWS_PROFILE=default

  # Bedrock models
  BEDROCK_MODEL_SONIC=amazon.nova-sonic-v1:0
  BEDROCK_MODEL_LITE=amazon.nova-lite-v1:0
  BEDROCK_MODEL_EMBEDDING=amazon.nova-pro-v1:0

  # Data stores
  REDIS_URL=redis://localhost:6379
  DATABASE_URL=postgresql+asyncpg://mc:mc@localhost:5432/missioncontrol

  # S3
  S3_BUCKET_EVIDENCE=mission-control-evidence-dev

  # Vector store
  OPENSEARCH_ENDPOINT=https://<collection>.us-east-1.aoss.amazonaws.com

  # App
  LOG_LEVEL=INFO
  DEMO_MODE=false
  API_KEY=changeme
  ```
- Add `docs/ENV.md` explaining each variable, which are required in local vs AWS mode, and how to pull secrets from Secrets Manager locally (`aws secretsmanager get-secret-value`).
- Backend reads via `python-dotenv`: `load_dotenv()` in `backend/config.py` with typed Pydantic Settings class.

**Dependencies:** Task 1.1.

**Expected output:** `.env.example` committed; `docs/ENV.md` describes every variable; backend Settings class validates at startup.

---

### Task 1.4 — CI Skeleton

**Description:** Add a GitHub Actions workflow that runs lint and tests for both backend and frontend on every push and PR. No deployment yet.

**Technical implementation notes:**
- File: `.github/workflows/ci.yml`. Jobs (can run in parallel):
  - `backend-lint`: `pip install ruff black`, `ruff check backend/ models/ agents/`, `black --check backend/ models/ agents/`.
  - `backend-test`: `pip install -e ".[dev]"`, `pytest backend/tests/ -x --tb=short`.
  - `frontend-lint`: `npm ci`, `npm run lint`.
  - `frontend-test`: `npm run test -- --run`.
- Backend smoke test (`backend/tests/test_smoke.py`): import `app` from `backend/main.py`; `GET /health` returns 200.
- Frontend smoke test: a single Vitest file asserting the App renders without crashing.
- Use `actions/setup-python@v5` and `actions/setup-node@v4`.
- Cache pip and npm via `actions/cache`.

**Dependencies:** Task 1.2.

**Expected output:** `.github/workflows/ci.yml` runs green on a clean repo; PR checks visible in GitHub.

---

### Task 2.6 — IAM Roles and Secrets Manager

**Description:** Define least-privilege IAM roles for ECS Fargate tasks and store sensitive config (DB credentials, any third-party keys) in AWS Secrets Manager. This prevents secrets from living in environment variables in plaintext and ensures infra is audit-ready.

**Technical implementation notes:**
- ECS Task Role policy: allow `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on all resources (or specific ARNs); `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` scoped to the evidence bucket ARN; `secretsmanager:GetSecretValue` scoped to secrets with prefix `mission-control/`; `aoss:APIAccessAll` scoped to the OpenSearch collection; `ssm:GetParameter` for any SSM parameters.
- Create Secrets Manager secrets:
  - `mission-control/db-url`: value = `postgresql+asyncpg://...`
  - `mission-control/api-key`: value = API key for gateway auth
- In CDK/Terraform, inject secrets as ECS env vars via `secrets` field (not `environment`), so values are fetched at task start and not visible in the console.
- Document in `docs/IAM.md` what each permission is for.

**Dependencies:** Tasks 2.2–2.5 (need resource ARNs to scope policies).

**Expected output:** Fargate task starts with role attached; `aws sts get-caller-identity` from within task shows the task role; no hardcoded credentials anywhere.

---

### Task 2.7 — Local Dev Docker Compose

**Description:** Provide a Docker Compose file so every engineer can spin up all backing services (Redis, Postgres, optional MinIO for S3) locally with one command, without needing an AWS account.

**Technical implementation notes:**
- File: `docker-compose.yml` at repo root.
  ```yaml
  services:
    redis:
      image: redis:7-alpine
      ports: ["6379:6379"]
    postgres:
      image: postgres:16-alpine
      environment:
        POSTGRES_USER: mc
        POSTGRES_PASSWORD: mc
        POSTGRES_DB: missioncontrol
      ports: ["5432:5432"]
      volumes:
        - ./infra/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    minio:
      image: minio/minio
      command: server /data --console-address ":9001"
      ports: ["9000:9000", "9001:9001"]
      environment:
        MINIO_ROOT_USER: minioadmin
        MINIO_ROOT_PASSWORD: minioadmin
  ```
- `infra/init.sql`: CREATE TABLE stubs for `missions`, `tasks`, `evidence` matching the schemas in `tasks.md`.
- `.env.local` (gitignored): `REDIS_URL=redis://localhost:6379`, `DATABASE_URL=postgresql+asyncpg://mc:mc@localhost:5432/missioncontrol`, `S3_BUCKET_EVIDENCE=evidence`, `AWS_ENDPOINT_URL_S3=http://localhost:9000`, `AWS_ACCESS_KEY_ID=minioadmin`, `AWS_SECRET_ACCESS_KEY=minioadmin`. Instruct in README to copy to `.env` for local dev.
- Add `make` targets or npm scripts for convenience: `make dev-up` = `docker compose up -d`, `make dev-down` = `docker compose down`.

**Dependencies:** Task 1.3; Tasks 2.2–2.4 (schema must match what infra creates in AWS).

**Expected output:** `docker compose up -d` starts all three services; backend can connect to Postgres and Redis; health check passes.

---

### Task 13.1 — Structured JSON Logging Standard

**Description:** Define and implement the project-wide logging format. All services — Voice Gateway, Orchestrator, Evidence Service, Agent runners — must emit structured JSON logs with consistent correlation IDs so any log can be filtered by `mission_id`, `agent_id`, or `evidence_id` in CloudWatch.

**Technical implementation notes:**
- Use `structlog` with JSON renderer in production (`RENDER=json`), pretty console in dev.
- Create `backend/logging_config.py`:
  ```python
  import structlog, logging

  def configure_logging(level: str = "INFO"):
      structlog.configure(
          processors=[
              structlog.contextvars.merge_contextvars,
              structlog.processors.add_log_level,
              structlog.processors.TimeStamper(fmt="iso"),
              structlog.processors.JSONRenderer(),
          ],
          wrapper_class=structlog.make_filtering_bound_logger(
              logging.getLevelName(level)
          ),
      )
  ```
- Context vars: `structlog.contextvars.bind_contextvars(mission_id=..., agent_id=..., request_id=...)` at the start of each request/task. All downstream log calls automatically include these fields.
- Key events to log: `mission_start`, `mission_status_change`, `agent_assigned`, `agent_heartbeat_missed`, `evidence_ingested`, `synthesis_start`, `mission_complete`, `error`.
- No PII in logs: do not log user speech text or raw evidence snippets at INFO; use DEBUG only.
- Document log fields in `docs/LOGGING.md`; share with all engineers so they bind correct context vars in their services.

**Dependencies:** Phases 4, 5, 6 need to be started so engineers know what context to bind. Set up the module early; engineers add `bind_contextvars` calls as they build.

**Expected output:** `structlog` emits JSON to stdout; CloudWatch ingests and allows `filter_log_events --filter-pattern '{ $.mission_id = "*" }'`.

---

### Task 14.1 — Seeded Demo Mission Script

**Description:** Implement a reliable, repeatable demo flow for the Sequoia pitch scenario. The script must produce a deterministic task graph so the demo does not depend on Nova Lite choosing the right decomposition live.

**Technical implementation notes:**
- Create `demo/seed_sequoia.py` (or a CLI via `argparse`):
  1. Call `POST /missions` with objective `"I'm pitching to Sequoia next week. Find their recent investments, partner priorities, founder complaints, and AI portfolio weaknesses."`.
  2. Immediately patch the task graph via internal function or `PATCH /missions/{id}` to a fixed seed graph with six tasks:
     - "Scrape sequoiacap.com for recent portfolio and partners" → OFFICIAL_SITE
     - "Search news and blogs for Sequoia 2024-2025 investments" → NEWS_BLOG
     - "Search Reddit/HN for founder complaints about Sequoia" → REDDIT_HN
     - "Search GitHub for AI projects in Sequoia portfolio" → GITHUB
     - "Retrieve financial data on recent Sequoia fund sizes" → FINANCIAL
     - "Find recent news about Sequoia AI strategy and bets" → RECENT_NEWS
  3. Trigger orchestrator to start planning loop.
  4. Print mission_id and poll status every 5 s until COMPLETE or timeout 60 s.
- Add `demo/run_demo.sh`: export env vars, call `python demo/seed_sequoia.py`, open browser to War Room URL with mission_id.
- Document in `docs/DEMO.md`: prerequisites, one-command run, expected timeline, what to say at each stage.

**Dependencies:** Phase 4 (Mission API), Phase 5 (Agents deployed), Phase 10 (Planning logic).

**Expected output:** `bash demo/run_demo.sh` starts a Sequoia mission; War Room shows agents deploying within 3 s, first evidence within 8 s, briefing within 45 s.

---

### Task 14.2 — Mock Mode for Offline Demo

**Description:** When `DEMO_MODE=true`, bypass real Bedrock/browser calls and replay a pre-built evidence dataset. The War Room UI still animates; no AWS account or internet required for slides.

**Technical implementation notes:**
- Create `demo/mock_evidence.json`: array of 12–15 EvidenceRecord objects for the Sequoia mission covering all six themes. Include realistic claims, sources (sequoiacap.com, TechCrunch, Reddit, etc.), confidence 0.7–0.95.
- In the orchestrator planning loop: if `DEMO_MODE=true`, skip Bedrock calls; immediately "assign" tasks and schedule `POST /evidence` calls from mock data at 2–5 s intervals using `asyncio.sleep`.
- In `models/sonic_client.py`: if `DEMO_MODE=true`, return a canned acknowledgement text (`"Mission accepted. Deploying six agents now."`) and a canned briefing without calling Bedrock.
- In `agents/browser_runner.py`: if `DEMO_MODE=true`, skip browser session; read from mock data.
- Document in `docs/DEMO.md`: set `DEMO_MODE=true` in `.env`, run seed script, open War Room.

**Dependencies:** Task 5.4, 6.1, Phase 8 (UI must be running).

**Expected output:** Full demo with animated War Room and mock evidence runs locally with only Docker Compose (no Bedrock calls).

---

### Task 14.3 — Demo Reset Endpoint

**Description:** `POST /demo/reset` wipes all mission state, evidence, and Redis keys for the current demo session. Operators can run it between back-to-back demos without restarting services.

**Technical implementation notes:**
- FastAPI router at `backend/routers/demo.py` (only mounted if `DEMO_MODE=true`).
- Handler: within a transaction — DELETE all rows from `evidence`, `tasks`, `missions`; FLUSHDB on Redis (or selective DEL of `mission:*`, `agent:*` keys); log the reset event.
- Guard: require `X-API-Key` header matching `API_KEY` env var (same key used for gateway auth).
- Return `204 No Content`.

**Dependencies:** Phase 4, 6, 9 all running.

**Expected output:** `curl -X POST /demo/reset -H "X-API-Key: changeme"` returns 204; subsequent `GET /missions` returns empty list; Redis has no mission keys.

---

### Task 14.4 — Architecture Diagram Export

**Description:** Produce a slide-ready PNG/SVG of the system architecture from the Mermaid diagram in `tasks.md`. Store in `docs/` for pitch decks and the README.

**Technical implementation notes:**
- Install Mermaid CLI: `npm install -g @mermaid-js/mermaid-cli`.
- Extract the Mermaid block from `tasks.md` into `docs/architecture.mmd`.
- Run: `mmdc -i docs/architecture.mmd -o docs/architecture.png -w 2400 -H 1600 -b transparent`.
- Also export SVG: `mmdc -i docs/architecture.mmd -o docs/architecture.svg`.
- Link both in README: `![Architecture](docs/architecture.png)`.
- Include a `make diagram` target that regenerates them.

**Dependencies:** None (diagram content is already in `tasks.md`).

**Expected output:** `docs/architecture.png` and `docs/architecture.svg` committed; render correctly in GitHub README preview.

---

### Task 14.5 — Load Test Script

**Description:** A script that fires 10 missions in parallel and measures: success count, p50/p95 time to COMPLETE, evidence count per mission, and errors. Used for regression and capacity checks before demo day.

**Technical implementation notes:**
- File: `demo/load_test.py` using `asyncio` + `httpx.AsyncClient`.
- Flow per mission: `POST /missions` → poll `GET /missions/{id}` every 3 s until `status == COMPLETE` or 120 s timeout → record elapsed time and `evidence_count`.
- Run 10 missions with 10 different objectives drawn from a list (variety avoids caching artefacts).
- Output: print a table and write `demo/load_test_results.csv` with columns: `mission_id, objective, status, elapsed_sec, evidence_count, error`.
- Calculate and print p50, p95 from the elapsed_sec column.
- Usage: `python demo/load_test.py --base-url http://localhost:8000 --concurrency 10`.

**Dependencies:** Phase 4 (missions API), Phase 12 (synthesis complete).

**Expected output:** Script runs; results CSV produced; p50 < 45 s on local mock mode; errors clearly reported.

---

## Quick Reference — Files You Own

```
.gitignore
README.md
.env.example
docs/ENV.md
docs/IAM.md
docs/LOGGING.md
docs/DEMO.md
docs/architecture.mmd
docs/architecture.png
docs/architecture.svg
.github/workflows/ci.yml
backend/pyproject.toml
backend/config.py              (Settings class)
backend/logging_config.py
backend/routers/demo.py
backend/tests/test_smoke.py
frontend/package.json
infra/init.sql
docker-compose.yml
demo/seed_sequoia.py
demo/mock_evidence.json
demo/run_demo.sh
demo/load_test.py
```
