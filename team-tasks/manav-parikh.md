# Mission Control — Tasks for Manav Parikh

**Role:** Cloud Infrastructure & Mission Orchestrator  
**GitHub:** [manavparikh01](https://github.com/manavparikh01)  
**LinkedIn:** [manavparikh10](https://www.linkedin.com/in/manavparikh10/)  
**Background:** AI Engineer at NJDEP; MSCS NYU; built LLM chatbots with LangChain + Azure AI Search; TA for Cloud Computing; AWS, Docker, Kubernetes, Python, React.

---

## Implementation Status

**Last updated:** March 2026

| Task | Status | Notes |
|------|--------|-------|
| 2.1 AWS Core Network & Compute | ⏳ Pending | Start here — everything else depends on VPC/ECS/ALB |
| 2.2 Redis / ElastiCache | ⏳ Pending | Depends on 2.1 |
| 2.3 Postgres RDS | ⏳ Pending | Depends on 2.1; use `infra/init.sql` schema |
| 2.4 S3 Buckets | ⏳ Pending | Depends on 2.1 |
| 2.5 OpenSearch Serverless | ⏳ Pending | Coordinate with Rahil on embedding dimension before creating index |
| 4.1 Mission State Machine | ⏳ Pending | Depends on 2.2, 2.3 |
| 4.2 Mission CRUD API | ⏳ Pending | Depends on 4.1 — unblocks Chinmay and Sariya |
| 4.3 Context Packet Builder | ⏳ Pending | Depends on 4.1 |
| 4.4 Task Graph (Nova Lite) | ⏳ Pending | Depends on 4.1, 4.3; creates `models/lite_client.py` (needed by Rahil) |
| 4.5 Orchestrator Planning Loop | ⏳ Pending | Depends on 4.3, 4.4, Phase 5 |
| 9.1 Redis Pub/Sub Channels | ⏳ Pending | Depends on 2.2, 4.1, 6.1 — unblocks Sariya's WS relay |
| 13.2 Metrics Emission | ⏳ Pending | Instrument after Phases 3–6 in place |
| 13.3 CloudWatch Dashboards | ⏳ Pending | Depends on 13.2 |
| 13.4 Distributed Tracing | ⏳ Pending | Depends on 13.1 (Bharath's logging setup) |

### What You're Unblocking

Your first four tasks (2.1–2.4 infra + 4.2 Mission API) directly unblock:
- **Chinmay** — can't connect voice gateway or agent pool to Redis/Postgres until 2.2, 2.3 are live
- **Rahil** — can't ingest evidence until 2.3 (Postgres) and 2.4 (S3) exist
- **Sariya** — `GET /missions/{id}` (Task 4.2) is needed for WS reconnect state refetch; ALB URL needed for CORS config

### What You Need First

The foundation is already in place from Bharath (Phase 1):
- `backend/config.py` — Settings class reads all your infra URLs from env
- `.env.example` — has placeholders for `REDIS_URL`, `DATABASE_URL`, `OPENSEARCH_ENDPOINT`, `S3_BUCKET_EVIDENCE`
- `backend/pyproject.toml` — all Python deps already pinned including `asyncpg`, `redis[hiredis]`, `boto3`, `sqlalchemy[asyncio]`
- `backend/main.py` — FastAPI app ready to mount your routers

**Your immediate next step:** set up the CDK/Terraform project in `infra/` and deploy Tasks 2.1–2.4 so the rest of the team can connect to real services.

---

## Why These Tasks

Your cloud engineering background (TA for Cloud Computing, AWS infra, Docker/K8s) makes you the natural owner of all AWS infrastructure. Your LangChain + LLM chatbot work at NJDEP maps directly onto building the Mission Orchestrator — the "brain" that plans agent deployment using Nova Lite. You also own the Redis pub/sub backbone and the CloudWatch observability layer.

---

## Task Summary

| Task | Phase | Description | Depends On | Status |
|------|-------|-------------|------------|--------|
| 2.1 | Infrastructure | AWS core network and compute (VPC, ECS Fargate, ALB) | Phase 1 | ⏳ Pending |
| 2.2 | Infrastructure | Redis / ElastiCache cluster | 2.1 | ⏳ Pending |
| 2.3 | Infrastructure | Postgres RDS or DynamoDB | 2.1 | ⏳ Pending |
| 2.4 | Infrastructure | S3 buckets | 2.1 | ⏳ Pending |
| 2.5 | Infrastructure | Vector store (OpenSearch Serverless) | 2.1 | ⏳ Pending |
| 4.1 | Orchestrator | Mission state machine and storage | 2.3 | ⏳ Pending |
| 4.2 | Orchestrator | Mission CRUD API | 4.1 | ⏳ Pending |
| 4.3 | Orchestrator | Context packet builder | 4.1 | ⏳ Pending |
| 4.4 | Orchestrator | Task graph construction (Nova Lite) | 4.1, 4.3 | ⏳ Pending |
| 4.5 | Orchestrator | Orchestrator planning loop | 4.3, 4.4 | ⏳ Pending |
| 9.1 | Streaming | Redis pub/sub channel definitions | 2.2, 4.1, 6.1 | ⏳ Pending |
| 13.2 | Observability | Metrics emission (CloudWatch / OTel) | Phase 3–6, 9 | ⏳ Pending |
| 13.3 | Observability | CloudWatch dashboards and alarms | 13.2 | ⏳ Pending |
| 13.4 | Observability | Distributed tracing (AWS X-Ray) | 13.1 | ⏳ Pending |

**Total: 14 tasks — 0 Done, 14 Pending**

---

## Coordination Map

| You need from | What |
|---------------|------|
| **Bharath** | `.env.example` and `backend/config.py` (Settings class) before you start; IAM role ARN (2.6) to attach to Fargate task |
| **Chinmay** | Voice Gateway service (Phase 3) must connect to your Redis and Postgres |
| **Rahil** | Evidence service (Phase 6) writes to your Postgres; vector pipeline (Phase 7) writes to your OpenSearch |
| **Sariya** | Frontend (Phase 8) connects to your ALB WebSocket endpoint and mission REST API |

---

## Full Task Details

---

### Task 2.1 — AWS Core Network and Compute

**Description:** Define VPC, subnets, ECS Fargate cluster, and Application Load Balancer. This is the compute foundation for every backend service.

**Technical implementation notes:**
- Choose CDK (TypeScript) in `infra/cdk/` or Terraform in `infra/terraform/`. CDK recommended given team's TypeScript comfort.
- VPC: `ec2.Vpc` with 2 AZs, public + private subnets. NAT Gateway for private subnets (single NAT for demo cost savings).
- ECS: `ecs.Cluster` in the VPC. One Fargate service for `backend` (starts with placeholder task definition; updated in later phases). CPU 1024, Memory 2048 for demo.
- ALB: `elbv2.ApplicationLoadBalancer` in public subnets. Listener on port 443 (HTTPS) with ACM cert; or port 80 for demo. Target group pointing to Fargate service. **Critical:** set ALB idle timeout to 300 s and enable stickiness for WebSocket support.
- Security groups: ALB SG allows 0.0.0.0/0 on 80/443; Fargate SG allows ALB SG on app port (e.g. 8000); Redis SG allows Fargate SG on 6379; RDS SG allows Fargate SG on 5432.
- CDK outputs: ALB DNS name, Fargate service name, cluster ARN. Store in SSM Parameter Store for reference.

**Dependencies:** Phase 1 complete; AWS account with admin credentials; CDK bootstrapped (`cdk bootstrap`).

**Expected output:** `cdk deploy` (or `terraform apply`) succeeds; placeholder Fargate service returns `{"status":"ok"}` from ALB health path `/health`.

**Subtasks:**
- 2.1.1 Create CDK/Terraform project in `infra/`.
- 2.1.2 VPC + subnets + NAT.
- 2.1.3 ECS cluster + placeholder Fargate service.
- 2.1.4 ALB + listener + target group; verify WebSocket works (test with `wscat`).

---

### Task 2.2 — Redis / ElastiCache

**Description:** Provision a single-node ElastiCache Redis 7 cluster in private subnets. Used for hot mission state, agent heartbeats, and pub/sub event streaming.

**Technical implementation notes:**
- CDK: `elasticache.CfnReplicationGroup` (or `CfnCacheCluster` for single node). `AutomaticFailoverEnabled: false` for demo. Parameter group: `default.redis7`. Subnet group covering private subnets. Security group allows Fargate SG on port 6379.
- Redis AUTH token optional for demo (VPC isolation is sufficient); if enabled, store token in Secrets Manager and reference in backend config.
- Output `REDIS_URL` (`redis://<endpoint>:6379`) as SSM parameter `/mission-control/redis-url`.
- Verify: `redis-cli -h <endpoint> ping` returns `PONG` from a Fargate task or bastion.

**Dependencies:** Task 2.1.

**Expected output:** Redis endpoint reachable from Fargate; backend `redis.asyncio.from_url(REDIS_URL)` connects; `SET foo bar` / `GET foo` work.

---

### Task 2.3 — Postgres or DynamoDB

**Description:** Provision the primary relational store for `missions`, `tasks`, and `evidence` metadata. RDS Postgres recommended for rich query support (JOIN tasks by mission, filter evidence by theme).

**Technical implementation notes:**
- RDS: `rds.DatabaseInstance` with Postgres 16, `db.t3.micro` (demo), single AZ. Private subnet group. Security group allows Fargate SG on 5432.
- DB name: `missioncontrol`. Master credentials via Secrets Manager (CDK auto-generates). Output secret ARN as SSM parameter `/mission-control/db-secret-arn`.
- **Schema** (align with `tasks.md` schemas; Bharath's `infra/init.sql` is the source of truth):
  ```sql
  CREATE TABLE missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    objective TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    task_graph JSONB,
    agent_ids TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    briefing TEXT,
    briefing_audio_s3_key TEXT,
    user_id TEXT
  );
  CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID REFERENCES missions(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    dependencies UUID[],
    assigned_agent_id TEXT,
    priority INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
  CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID REFERENCES missions(id) ON DELETE CASCADE,
    agent_id TEXT,
    claim TEXT NOT NULL,
    summary TEXT,
    source_url TEXT,
    snippet TEXT,
    screenshot_s3_key TEXT,
    confidence FLOAT DEFAULT 0.8,
    novelty FLOAT DEFAULT 1.0,
    theme TEXT,
    embedding_id TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
  );
  CREATE INDEX evidence_mission_ts ON evidence(mission_id, timestamp DESC);
  ```
- For local dev, Bharath's `docker-compose.yml` runs Postgres with `infra/init.sql` mounted.

**Dependencies:** Task 2.1.

**Expected output:** RDS instance created; `asyncpg.connect(DATABASE_URL)` from Fargate succeeds; schema initialized.

---

### Task 2.4 — S3 Buckets

**Description:** Create S3 bucket for evidence screenshots and raw browser artifacts. Bucket must be private; frontend accesses via presigned URLs generated by backend.

**Technical implementation notes:**
- CDK: `s3.Bucket` with `blockPublicAccess: BlockPublicAccess.BLOCK_ALL`, `encryption: BucketEncryption.S3_MANAGED`, `removalPolicy: RemovalPolicy.RETAIN` (do not lose evidence on stack teardown).
- CORS configuration: allow `GET` from frontend origin (or `*` for demo).
- Lifecycle rule: transition objects to `INTELLIGENT_TIERING` after 30 days.
- Output bucket name as SSM parameter `/mission-control/s3-bucket-evidence`.
- Naming: `mission-control-evidence-{account_id}-{region}` (globally unique).

**Dependencies:** Task 2.1.

**Expected output:** Bucket exists; backend can `PutObject` (screenshot upload) and generate presigned `GetObject` URL with 1-hour expiry; URL loads image in browser.

---

### Task 2.5 — Vector Store (OpenSearch Serverless)

**Description:** Create an OpenSearch Serverless collection and k-NN index for evidence embeddings. Must be reachable from Fargate in the same VPC.

**Technical implementation notes:**
- CDK / AWS console: create collection type `VECTORSEARCH`, name `mission-control-vectors`.
- Network policy: VPC endpoint from the VPC (or public for demo with IP-based access policy).
- Data access policy: allow `aoss:*` for the ECS task role (Task 2.6) and your IAM user.
- Once collection is active, create index via `opensearchpy` client:
  ```python
  index_body = {
    "settings": {"index": {"knn": True}},
    "mappings": {
      "properties": {
        "embedding": {"type": "knn_vector", "dimension": 1024},
        "mission_id": {"type": "keyword"},
        "evidence_id": {"type": "keyword"},
        "text_summary": {"type": "text"}
      }
    }
  }
  client.indices.create("evidence_vectors", body=index_body)
  ```
- Output collection endpoint as SSM parameter `/mission-control/opensearch-endpoint`.
- Coordinate with Rahil (Phase 7) on the embedding dimension — confirm from Bedrock Nova docs before creating the index.

**Dependencies:** Task 2.1; coordinate with Rahil for dimension.

**Expected output:** Index `evidence_vectors` exists; backend can index a document and run a k-NN search (smoke test in Phase 7).

---

### Task 4.1 — Mission State Machine and Storage

**Description:** Implement the mission lifecycle in code: `PENDING → ACTIVE → SYNTHESIZING → COMPLETE` (and `FAILED`). Persist every transition to Postgres and emit a `TIMELINE_EVENT` to Redis pub/sub.

**Technical implementation notes:**
- File: `backend/missions/state_machine.py`. Use a simple enum + allowed transitions dict:
  ```python
  from enum import StrEnum

  class MissionStatus(StrEnum):
      PENDING = "PENDING"
      ACTIVE = "ACTIVE"
      SYNTHESIZING = "SYNTHESIZING"
      COMPLETE = "COMPLETE"
      FAILED = "FAILED"

  ALLOWED_TRANSITIONS = {
      MissionStatus.PENDING: {MissionStatus.ACTIVE, MissionStatus.FAILED},
      MissionStatus.ACTIVE: {MissionStatus.SYNTHESIZING, MissionStatus.FAILED},
      MissionStatus.SYNTHESIZING: {MissionStatus.COMPLETE, MissionStatus.FAILED},
      MissionStatus.COMPLETE: set(),
      MissionStatus.FAILED: set(),
  }

  async def transition(mission_id: UUID, new_status: MissionStatus, db, redis):
      mission = await db.get_mission(mission_id)
      if new_status not in ALLOWED_TRANSITIONS[mission.status]:
          raise ValueError(f"Invalid transition {mission.status} → {new_status}")
      await db.update_mission_status(mission_id, new_status)
      await redis.publish(
          f"mission:{mission_id}:events",
          json.dumps({"type": "MISSION_STATUS", "mission_id": str(mission_id), "status": new_status})
      )
  ```
- DB layer: `backend/missions/repository.py` — async functions using `asyncpg` or SQLAlchemy async. Functions: `create_mission`, `get_mission`, `update_mission_status`, `update_mission_briefing`.
- Alembic (or raw SQL) migration for the schema defined in Task 2.3.

**Dependencies:** Phase 2 DB (Task 2.3); Redis (Task 2.2).

**Expected output:** Mission record created and transitions correctly; invalid transitions raise exceptions; every transition writes a `MISSION_STATUS` event to Redis.

---

### Task 4.2 — Mission CRUD API

**Description:** Expose `POST /missions`, `GET /missions/{id}`, `PATCH /missions/{id}`, `GET /missions/{id}/tasks`. These are the primary REST endpoints used by Sonic tool implementations and the War Room UI.

**Technical implementation notes:**
- File: `backend/routers/missions.py`. FastAPI `APIRouter`.
- `POST /missions`: accept `{ "objective": str }`, create mission in PENDING, return `MissionRecord`. After creation, publish to Redis and kick off orchestrator planning (async background task or call via internal queue).
- `GET /missions/{id}`: return `MissionRecord` joined with `evidence_count` (SELECT COUNT from evidence table) and optional `tasks: list[TaskNode]` if `?include_tasks=true`.
- `PATCH /missions/{id}`: accept `{ "status"?: str, "briefing"?: str }`. Validate status via state machine. Return updated record.
- `GET /missions/{id}/tasks`: return list of `TaskNode` for mission, ordered by `priority DESC, created_at ASC`.
- Pydantic models in `backend/missions/schemas.py` matching `tasks.md` schema tables.
- Auth: read `X-API-Key` header; compare to `settings.API_KEY`. Return 401 if missing/wrong (simple for demo).

**Dependencies:** Task 4.1.

**Expected output:** All four endpoints return correct shapes; tested with `pytest` (mock DB); Sonic can call `POST /missions` and get a UUID back.

---

### Task 4.3 — Context Packet Builder

**Description:** Build the `MissionContextPacket` from current mission state. This is the structured snapshot sent to Nova Lite each planning cycle — never the full conversation history.

**Technical implementation notes:**
- File: `backend/orchestrator/context_builder.py`.
- Function signature: `async def build_context_packet(mission_id: UUID, db, redis) -> MissionContextPacket`.
- Steps:
  1. Fetch `MissionRecord` from DB.
  2. Fetch `TaskNode[]` from DB.
  3. Fetch agent states from Redis: `HGETALL agent:{id}` for each agent_id in mission.
  4. Fetch top 10 evidence (by `confidence * novelty` desc) from DB for the mission.
  5. Fetch contradictions: stub as `[]` until Phase 7.5 is complete.
  6. Fetch open questions: derive from tasks with status `PENDING` or `ASSIGNED` (their descriptions).
  7. Fetch conversation summary: `LRANGE mission:{id}:conversation_summary 0 0` from Redis (gateway stores last summary there).
  8. Compute `time_elapsed_sec` from `mission.created_at`.
- Return Pydantic `MissionContextPacket` model.

**Dependencies:** Task 4.1; evidence stub (returns empty list if Phase 6 not done yet).

**Expected output:** `build_context_packet(mission_id, ...)` returns a valid packet; can be serialized to JSON and sent to Nova Lite.

---

### Task 4.4 — Task Graph Construction (Nova Lite)

**Description:** From the mission objective, call Nova Lite to produce a task graph: a list of TaskNodes with descriptions, agent types, dependencies, and priorities. Persist as linked TaskNodes in Postgres.

**Technical implementation notes:**
- File: `backend/orchestrator/task_planner.py`.
- Nova Lite client: similar to Sonic wrapper — `boto3` Bedrock `converse` (non-streaming). Model id from `settings.BEDROCK_MODEL_LITE`.
- System prompt:
  ```
  You are a mission planning system. Given a user's intelligence mission objective, 
  decompose it into a list of research tasks for specialized browser agents.
  Respond ONLY with a valid JSON array. Each element: 
  { "description": str, "agent_type": one of [OFFICIAL_SITE, NEWS_BLOG, REDDIT_HN, GITHUB, FINANCIAL, RECENT_NEWS], "priority": int 1-10 }
  Do not include dependencies unless one task must strictly follow another.
  ```
- Parse response: `json.loads(response_text)`. Validate with Pydantic. On parse error: retry once; on second failure, fall back to a single generic `OFFICIAL_SITE` task.
- Insert all tasks via `db.create_task(mission_id, ...)` in a transaction. Update `mission.task_graph = JSONB(tasks)`.
- Add `models/lite_client.py`: thin wrapper around `boto3` `converse` with retries and logging.

**Dependencies:** Task 4.1, 4.3; Bedrock Nova Lite access.

**Expected output:** `plan_tasks(mission_id, objective, db)` creates 4–6 TaskNodes in DB; each has correct `agent_type` and `priority`.

---

### Task 4.5 — Orchestrator Planning Loop

**Description:** The core planning loop: every 10–15 s (or triggered by a Redis event), build the context packet, call Nova Lite for decisions, and execute those decisions (assign agents, redirect, trigger synthesis).

**Technical implementation notes:**
- File: `backend/orchestrator/planner.py`. `async def planning_loop(mission_id, db, redis)`.
- Loop:
  1. Build context packet (Task 4.3).
  2. If stopping criteria met (Task 10.5): transition to SYNTHESIZING and break.
  3. Call Nova Lite with context packet as structured input. System prompt instructs Lite to output a JSON action list: `[{ "action": "assign", "agent_id": "agent_0", "task_id": "..." }, ...]`. Actions: `assign`, `redirect`, `no_op`.
  4. For each action: dispatch via Redis `LPUSH agent:{id}:commands <AgentCommand JSON>` (see Task 11.1).
  5. Sleep 10 s. Repeat.
- Start loop as `asyncio.create_task` when mission transitions to ACTIVE (in `POST /missions` handler).
- Store loop task reference in a dict keyed by `mission_id`; cancel on COMPLETE/FAILED.
- Do NOT store prior Lite responses; each iteration only sees the current context packet.

**Dependencies:** Tasks 4.3, 4.4; Phase 5 for agent dispatch to work end-to-end.

**Expected output:** Planning loop starts on mission creation; logs show context packets and Lite decisions every 10 s; tasks get assigned when agents are idle.

---

### Task 9.1 — Redis Pub/Sub Channel Definitions

**Description:** Define and document the Redis channels used for real-time event streaming. Implement publisher helpers used by the orchestrator and evidence service.

**Technical implementation notes:**
- File: `backend/streaming/publisher.py`.
- Channel naming:
  - `mission:{mission_id}:events` — mission status changes, timeline events, briefing chunks.
  - `agent:{agent_id}:findings` — new evidence from a specific agent.
- Publisher helpers:
  ```python
  async def publish_mission_event(redis, mission_id: UUID, event: dict):
      await redis.publish(f"mission:{mission_id}:events", json.dumps(event))

  async def publish_agent_finding(redis, agent_id: str, evidence: dict):
      await redis.publish(f"agent:{agent_id}:findings", json.dumps(evidence))
  ```
- Event envelope: `{ "type": <WS message type>, "payload": {...}, "ts": <ISO timestamp> }`.
- Document all event types in `docs/EVENTS.md` with sample payloads for each of: `AGENT_UPDATE`, `EVIDENCE_FOUND`, `MISSION_STATUS`, `TIMELINE_EVENT`, `BRIEFING_CHUNK`.
- The WebSocket relay (Task 9.2, owned by Chinmay) subscribes to these channels and forwards to clients.

**Dependencies:** Task 2.2 (Redis up), Task 4.1 (orchestrator publishes on transition), Task 6.1 (evidence service publishes on ingest).

**Expected output:** `publish_mission_event` and `publish_agent_finding` tested with a Redis subscriber in pytest; correct message shapes per WS contract in `tasks.md`.

---

### Task 13.2 — Metrics Emission

**Description:** Instrument all services to emit the metrics defined in `tasks.md`'s Observability Metrics table using CloudWatch PutMetricData or OpenTelemetry.

**Technical implementation notes:**
- Use `boto3` `cloudwatch.put_metric_data` or the `aws-embedded-metrics` Python package for zero-cost batching.
- Alternatively use OpenTelemetry SDK with OTLP exporter → CloudWatch ADOT collector.
- Instrument the following (add decorators or inline calls):
  - `mission_start_total`: increment on `POST /missions`.
  - `mission_duration_seconds`: record on `MISSION_STATUS = COMPLETE` or `FAILED`.
  - `agent_task_duration_seconds` by `agent_type`: record when task transitions to DONE.
  - `evidence_ingested_total`: increment on `POST /evidence`.
  - `sonic_first_token_seconds`: measured by Chinmay in the voice gateway; you wire the metric emission.
  - `orchestrator_planning_duration_seconds`: time each planning cycle.
  - `websocket_connections_active`: gauge incremented/decremented in WS connect/disconnect.
  - `agent_heartbeat_missed_total`: increment in watchdog (Task 11.2).
- Wrap timing with a context manager or decorator in `backend/metrics.py`.

**Dependencies:** Phases 3–6, 9 must have instrumentation points.

**Expected output:** Metrics visible in CloudWatch; can filter by dimension (e.g. `agent_type=FINANCIAL`).

---

### Task 13.3 — CloudWatch Dashboards and Alarms

**Description:** Create a CloudWatch dashboard for ops visibility and alarms for critical failure conditions.

**Technical implementation notes:**
- Dashboard widgets (JSON or CDK `cloudwatch.Dashboard`):
  - Line graph: `mission_start_total` and `mission_duration_seconds` p50/p95.
  - Line graph: `evidence_ingested_total` over time.
  - Single value: `websocket_connections_active`.
  - Bar chart: `agent_task_duration_seconds` by `agent_type` p95.
  - Single value: `sonic_first_token_seconds` p95.
- Alarms (CDK `cloudwatch.Alarm` + SNS topic → email):
  - `mission_duration_seconds` max > 120 s: "Mission stuck".
  - `agent_heartbeat_missed_total` sum > 0 in 5 min: "Agent timeout detected".
  - HTTP 5xx rate > 5% for 5 min: "Backend error spike".
- Store dashboard JSON in `infra/dashboard.json`; deploy via CDK or `aws cloudwatch put-dashboard`.

**Dependencies:** Task 13.2.

**Expected output:** Dashboard visible in CloudWatch console during demo; at least one alarm fires correctly in a test (simulate a timeout).

---

### Task 13.4 — Distributed Tracing (AWS X-Ray)

**Description:** Add AWS X-Ray tracing so a single voice request can be traced end-to-end: Sonic call → orchestrator → agent → evidence ingest.

**Technical implementation notes:**
- Install: `aws-xray-sdk` in Python. Add `XRayMiddleware` to FastAPI (`from aws_xray_sdk.ext.aiohttp.middleware import xray_middleware` or `from aws_xray_sdk.ext.fastapi.middleware import FastAPIInstrumentor`).
- Instrument `boto3` clients: `from aws_xray_sdk.core import patch_all; patch_all()` — automatically traces `boto3`, `httpx`, `asyncpg`.
- Propagate trace id:
  - In Redis published events, include `"trace_id": xray.current_trace_id()`.
  - In agent commands, include `trace_id` field so agent can resume the segment.
- FastAPI middleware: start a segment named `mission-control-backend` for each request; add annotations `mission_id`, `agent_id`.
- ECS task: ensure X-Ray daemon runs as a sidecar container in the Fargate task definition (CDK: add container `xray-daemon`, image `amazon/aws-xray-daemon`, port 2000/UDP).

**Dependencies:** Task 13.1 (logging must be set up first).

**Expected output:** Requests appear in X-Ray console as traces; clicking a trace shows sub-segments for Bedrock calls, DB queries, and Redis publishes.

---

## Quick Reference — Files You Own

```
infra/cdk/                          (or infra/terraform/)
  lib/vpc-stack.ts
  lib/ecs-stack.ts
  lib/redis-stack.ts
  lib/rds-stack.ts
  lib/s3-stack.ts
  lib/opensearch-stack.ts
backend/missions/
  state_machine.py
  repository.py
  schemas.py
backend/routers/missions.py
backend/orchestrator/
  context_builder.py
  task_planner.py
  planner.py
models/lite_client.py
backend/streaming/publisher.py
docs/EVENTS.md
backend/metrics.py
infra/dashboard.json
```
