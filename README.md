# VoiceAI — Mission Control (Dispatch)

A **voice-driven AI intelligence command center** powered by AWS Amazon Nova: speak a mission objective, and the system coordinates browser agents to gather evidence, synthesize findings, and stream results to a War Room UI.

---

## Architecture (high level)

```mermaid
flowchart LR
  Voice[Voice / Nova Sonic]
  Orch[Orchestrator / Nova Lite]
  Agents[Browser Agents]
  Evidence[Evidence Layer]
  UI[War Room UI]

  Voice --> Orch
  Orch --> Agents
  Agents --> Evidence
  Evidence --> UI
  UI --> Voice
```

Voice input drives the orchestrator; the orchestrator deploys agents; agents emit evidence; evidence is scored, stored, and streamed to the frontend.

---

## Prerequisites

| Tool       | Minimum | Notes |
|-----------|---------|--------|
| Python    | 3.12+   | [python.org](https://www.python.org/downloads/) or `brew install python@3.12` |
| Node.js   | 20+     | [nodejs.org](https://nodejs.org/) or `brew install node` |
| Docker    | Recent  | For Redis, Postgres, MinIO — [docker.com](https://www.docker.com/products/docker-desktop) |
| AWS CLI   | 2.x     | For Bedrock and secrets — [AWS CLI install](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| Git       | Recent  | Pre-installed on macOS; `brew install git` if needed |

---

## Directory layout

```
VoiceAI/
├── tasks.md           # Full system engineering plan
├── CLAUDE.md          # Getting started and repo structure (read this next)
├── team-tasks/        # Per-engineer task files
├── backend/           # FastAPI backend
├── frontend/          # React + Vite War Room UI
├── agents/            # Browser agent system (prompts in agents/prompts/)
├── models/            # Nova Sonic, Lite, Embedding wrappers
├── infra/             # AWS CDK (infra/cdk/)
└── docs/              # ENV, events, architecture docs
```

See [CLAUDE.md](CLAUDE.md) for the full repository structure and file-by-file description.

---

## Quick start

1. **Clone and branch**
   ```bash
   git clone <repo-url>
   cd VoiceAI
   git checkout -b <your-name>/setup
   ```

2. **Environment**  
   Copy `.env.example` to `.env` and set `AWS_REGION`, `AWS_PROFILE`, and any required URLs (see [docs/ENV.md](docs/ENV.md) when available).

3. **Local services**  
   Start Redis, Postgres, and MinIO:
   ```bash
   docker compose up -d
   ```

4. **Backend**  
   From repo root (after Task 1.2):
   ```bash
   cd backend && pip install -e ".[dev]" && uvicorn main:app --reload --port 8000
   ```

5. **Frontend**  
   In another terminal (after Task 1.2):
   ```bash
   cd frontend && npm install && npm run dev
   ```

For detailed setup, AWS Bedrock access, and demo mode, see **[CLAUDE.md](CLAUDE.md)**.

---

## Links

- **[tasks.md](tasks.md)** — Full engineering plan and phases
- **[CLAUDE.md](CLAUDE.md)** — Single source of truth for setup and repo structure
- **[team-tasks/](team-tasks/)** — Individual task files (bharath-gera, manav-parikh, rahil-singhi, chinmay-shringi, sariya-rizwan)
