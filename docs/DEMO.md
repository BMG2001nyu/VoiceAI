# Demo Guide

## Prerequisites

- Docker Desktop running (for Redis + Postgres + MinIO)
- Backend virtual environment active
- Frontend `npm install` done

## Quick Start

```bash
# 1. Start local services
make dev-up

# 2. Start backend
cd backend && source venv/bin/activate
DEMO_MODE=true uvicorn main:app --reload --port 8000

# 3. Start frontend (separate terminal)
cd frontend && npm run dev

# 4. Run demo
bash demo/run_demo.sh
```

## Mock Mode (DEMO_MODE=true)

When `DEMO_MODE=true`:
- Nova Sonic returns canned voice responses (no AWS API calls)
- Browser agents read from `demo/mock_evidence.json` instead of browsing
- The DLQ worker still runs (retries any failed mock ingests)
- The demo reset endpoint is available at `POST /demo/reset`

## Demo Reset

Between back-to-back demos:

```bash
curl -X POST http://localhost:8000/demo/reset -H "X-API-Key: changeme"
```

This wipes all missions, evidence, tasks, and Redis keys.

## Demo Flow

1. Open War Room at http://localhost:5173
2. Run `bash demo/run_demo.sh`
3. Watch agents deploy (3-5 seconds)
4. Evidence cards stream in (8-30 seconds)
5. Final briefing delivered (45-60 seconds)

## Mock Evidence

The file `demo/mock_evidence.json` contains 12 pre-built evidence records covering all 6 agent types:

| Theme | Count | Agent |
|-------|-------|-------|
| Partner Priorities | 1 | agent_0 |
| Strategy | 3 | agent_0, agent_5 |
| AI Portfolio | 2 | agent_1 |
| Founder Complaints | 2 | agent_2 |
| Technical | 2 | agent_3 |
| Financial | 2 | agent_4 |

## Troubleshooting

### Backend not reachable
Start it with: `cd backend && uvicorn main:app --reload --port 8000`

### Docker not running
Start with: `make dev-up` or `docker compose up -d`

### Evidence not appearing
Check `GET /internal/dlq/count` — if > 0, evidence ingestion is failing. Check Postgres connection.
