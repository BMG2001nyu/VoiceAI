# Deploying to Vercel (Frontend and Backend)

This document describes how to deploy the Mission Control frontend and backend using the Vercel CLI. The repo uses two separate Vercel projects: one for the frontend and one for the backend.

---

## Prerequisites

- [Vercel CLI](https://vercel.com/docs/cli) installed (`npm i -g vercel` or `npx vercel`).
- Vercel account; log in with `vercel login` if needed.

---

## 1. Frontend deployment

1. From the repo root:
   ```bash
   cd frontend
   npx vercel
   ```
2. When prompted, link to a new or existing Vercel project (e.g. name it `missioncontrol-frontend`).
3. Set environment variables in the [Vercel dashboard](https://vercel.com/dashboard) for this project (or via `vercel env add`):
   - **`VITE_API_URL`** — Backend API base URL (e.g. `https://<your-backend>.vercel.app`). Set this after the backend is deployed.
   - **`VITE_WS_URL`** — Backend WebSocket base URL (same as API origin). **Note:** WebSockets do not work when the backend runs on Vercel serverless; see [Backend WebSocket limitations](#backend-websocket-limitations) below.
4. Deploy to production:
   ```bash
   npx vercel --prod
   ```

The frontend is a static Vite SPA. Configuration is in `frontend/vercel.json` (build command, output directory `dist`).

---

## 2. Backend deployment

1. From the repo root:
   ```bash
   cd backend
   npx vercel
   ```
2. Link to a new or existing Vercel project (e.g. `missioncontrol-backend`).
3. Set environment variables for the backend project. Required (or recommended) for a working API:
   - **`DATABASE_URL`** — Postgres connection URL. On Vercel you must use a **serverless-friendly** Postgres provider (e.g. [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres), [Neon](https://neon.tech)). Standard long-lived connection URLs from a classic RDS/Compose Postgres may hit connection limits under serverless.
   - **`REDIS_URL`** — Redis connection URL. Use a **serverless-friendly** Redis such as [Upstash Redis](https://upstash.com) (HTTP or serverless-compatible client). Traditional Redis (ElastiCache, local) is not ideal for Vercel’s short-lived functions.
   - **`NOVA_API_KEY`** — For mission task decomposition and optional model features.
   - **`DEMO_MODE`** — Set to `true` to disable X-Ray tracing and optional features that assume long-lived processes.
   - **`API_KEY`** — For `/demo/reset` and internal routes (e.g. `changeme` or a secret).
4. Deploy to production:
   ```bash
   npx vercel --prod
   ```

The backend is exposed as a single FastAPI serverless function. The entrypoint is defined in `backend/pyproject.toml` as `[project.scripts] app = "main:app"`. Build exclusions (tests, cache, venv) are in `backend/vercel.json`.

---

## 3. Backend WebSocket limitations

**Vercel serverless does not support long-lived WebSocket connections.** The following backend routes will **not** work when the backend is deployed on Vercel:

- **`/ws/voice`** — Real-time voice (Nova Sonic) gateway.
- **`/ws/mission/{mission_id}`** — Mission event stream (agent updates, evidence, timeline).

Calls to these endpoints may return 502, time out, or fail to maintain a connection. The REST API (e.g. `/health`, `/missions`, `/evidence`) works as usual.

To get full real-time and voice functionality you would need either:

- An external WebSocket service (e.g. Rivet, PushFlo) plus your backend calling it, or  
- Hosting the backend on a platform that supports WebSockets (e.g. Railway, Render, Fly.io).

---

## 4. Data stores on Vercel (summary)

| Store    | Local / AWS                         | Vercel (serverless)                          |
|----------|-------------------------------------|----------------------------------------------|
| Postgres | Docker Compose / RDS                | **Vercel Postgres** or **Neon** (serverless) |
| Redis    | Docker Compose / ElastiCache         | **Upstash Redis** (serverless-friendly)       |

See [docs/ENV.md](ENV.md) for full environment variable reference. For Vercel, set `DATABASE_URL` and `REDIS_URL` to the URLs provided by the chosen serverless Postgres and Redis providers.

---

## 5. Post-deploy verification

- **Frontend:** Open the Vercel frontend URL; the War Room UI should load. If `VITE_API_URL` is set to the backend URL, API calls will go to the backend.
- **Backend:** Run:
  ```bash
  curl https://<your-backend>.vercel.app/health
  ```
  Expected: `{"status":"ok"}`. You can also test `POST /missions` with a JSON body once `DATABASE_URL` and `REDIS_URL` are set.

---

## 6. Troubleshooting backend 500 / function crash

If the backend returns **500 Internal Server Error** or **FUNCTION_INVOCATION_FAILED**:

1. **Check logs** — In the Vercel dashboard, open your backend project → Deployments → select the deployment → **Logs** (or run `vercel inspect <deployment-url> --logs`). The log will show the Python traceback (e.g. missing `agents` package, or DB/Redis connection failure).

2. **Ensure Root Directory is `backend`** — In Vercel → Project Settings → General → **Root Directory** must be `backend` (or leave empty if you deploy from repo root). Deploying from `backend/` with Root Directory set to `backend` ensures the build can run `cp -r ../agents .` so the `agents` package is available.

3. **`/health` works but `/missions` or `/evidence` return 503** — The app starts without DB/Redis so `/health` always returns 200. Set **`DATABASE_URL`** and **`REDIS_URL`** in the Vercel project (Environment Variables), then redeploy. Use serverless-friendly Postgres (e.g. Neon, Vercel Postgres) and Redis (e.g. Upstash).

4. **Optional: `DEMO_MODE=true`** — Reduces reliance on X-Ray and long-lived features. Set this if you see tracing-related errors in the logs.
