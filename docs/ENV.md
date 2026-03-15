# Environment Variable Reference

Copy `.env.example` to `.env` at the repo root and fill in the values for your environment.

```bash
cp .env.example .env
```

Variables are loaded by `backend/config.py` via `pydantic-settings`. Any variable can be overridden at runtime by setting it in the shell environment.

---

## AWS

### `AWS_REGION`
- **What it does:** AWS region used for all Bedrock, S3, and Secrets Manager calls.
- **Default:** `us-east-1`
- **Local dev:** Use `us-east-1` unless the team specifies otherwise.
- **AWS deployment:** Must match the region where Bedrock model access was approved.

### `AWS_PROFILE`
- **What it does:** Named AWS CLI credential profile to use (from `~/.aws/credentials`).
- **Default:** `default`
- **Local dev:** Set to the profile configured via `aws configure`.
- **AWS deployment:** Not used — credentials are provided via ECS task IAM role. Leave as `default` or unset.

---

## Bedrock Models

### `BEDROCK_MODEL_SONIC`
- **What it does:** Model ID for Amazon Nova Sonic, used by the voice gateway for real-time speech I/O.
- **Default:** `amazon.nova-sonic-v1:0`
- **Local dev:** Keep the default; Nova Sonic is always in `us-east-1`.
- **AWS deployment:** Same default. Override only if AWS publishes a new revision.

### `BEDROCK_MODEL_LITE`
- **What it does:** Model ID for Amazon Nova Lite, used by the orchestrator planning loop and task decomposition.
- **Default:** `amazon.nova-lite-v1:0`
- **Local dev:** Keep the default.
- **AWS deployment:** Same default.

### `BEDROCK_MODEL_EMBEDDING`
- **What it does:** Model ID for the embedding model used to index and query evidence in OpenSearch.
- **Default:** `amazon.nova-pro-v1:0`
- **Local dev:** Keep the default.
- **AWS deployment:** Same default. Must match the dimension constant in `models/embedding_client.py`.

---

## Data Stores

### `REDIS_URL`
- **What it does:** Connection URL for Redis. Used for pub/sub mission events, agent heartbeats, and task queue.
- **Default:** `redis://localhost:6379`
- **Local dev:** Start Redis via Docker Compose (`docker compose up -d`). Default URL works out of the box.
- **AWS deployment:** Set to the ElastiCache Redis endpoint output by the CDK stack (e.g. `redis://<host>:6379`).
- **Pull from Secrets Manager:**
  ```bash
  aws secretsmanager get-secret-value --secret-id mission-control/redis-url --query SecretString --output text
  ```

### `DATABASE_URL`
- **What it does:** SQLAlchemy-compatible async connection URL for Postgres. Stores mission state, agent records, and evidence metadata.
- **Default:** `postgresql+asyncpg://mc:mc@localhost:5432/missioncontrol`
- **Local dev:** Start Postgres via Docker Compose. Default URL and credentials match the Compose config.
- **AWS deployment:** Set to the RDS endpoint from the CDK stack output.
- **Pull from Secrets Manager:**
  ```bash
  aws secretsmanager get-secret-value --secret-id mission-control/database-url --query SecretString --output text
  ```

---

## S3

### `S3_BUCKET_EVIDENCE`
- **What it does:** Name of the S3 bucket (or MinIO bucket in local dev) where browser agent screenshots and raw evidence files are stored.
- **Default:** `mission-control-evidence-dev`
- **Local dev:** MinIO (started via Docker Compose) is used as a local S3 substitute. Create the bucket via the MinIO console at `http://localhost:9001` (login: `minioadmin` / `minioadmin`) or let the backend auto-create it on startup.
- **AWS deployment:** Set to the bucket name output by the CDK stack.

---

## Vector Store

### `OPENSEARCH_ENDPOINT`
- **What it does:** HTTPS endpoint for the Amazon OpenSearch Serverless collection used to store and query evidence embeddings.
- **Default:** None — **required in AWS deployment mode.**
- **Local dev:** Not required if `DEMO_MODE=true`. If running the full evidence pipeline locally, you need an OpenSearch endpoint (either an AWS AOSS collection or a local OpenSearch container).
- **AWS deployment:** Set to the collection endpoint output by the CDK stack (e.g. `https://<id>.us-east-1.aoss.amazonaws.com`).
- **Pull from Secrets Manager:**
  ```bash
  aws secretsmanager get-secret-value --secret-id mission-control/opensearch-endpoint --query SecretString --output text
  ```

---

## App

### `LOG_LEVEL`
- **What it does:** Minimum log level for `structlog`. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`.
- **Default:** `INFO`
- **Local dev:** Use `DEBUG` for verbose output during development.
- **AWS deployment:** Use `INFO` or `WARNING` to reduce log volume.

### `DEMO_MODE`
- **What it does:** When `true`, stubs out Nova Sonic, browser agents, and Bedrock calls with canned responses. No real AWS calls are made. Redis and Postgres are still required.
- **Default:** `false`
- **Local dev:** Set to `true` if you do not have AWS Bedrock access yet.
- **AWS deployment:** Always `false`.

### `AGENT_POOL_SIZE`
- **What it does:** Number of browser agents in the pool. Each agent runs one browsing task at a time.
- **Default:** `6`
- **Local dev:** Keep default. Reduce to `2` for faster startup during testing.
- **AWS deployment:** `6` (matched to ECS task CPU allocation).

### `BACKEND_URL`
- **What it does:** Base URL for the backend API. Used by browser agents to POST evidence.
- **Default:** `http://localhost:8000`
- **Local dev:** Keep default.
- **AWS deployment:** Set to the ALB DNS output from CDK (e.g., `http://<alb-dns>`).

### `API_KEY`
- **What it does:** Static bearer token checked on all backend API routes (`X-API-Key` header). Change before any public deployment.
- **Default:** `changeme`
- **Local dev:** Keep `changeme` for local testing.
- **AWS deployment:** Set to a strong random value. Store in Secrets Manager.
- **Pull from Secrets Manager:**
  ```bash
  aws secretsmanager get-secret-value --secret-id mission-control/api-key --query SecretString --output text
  ```

---

## Nova API

### `NOVA_API_KEY`
- **What it does:** Bearer token for the Nova API at `api.nova.amazon.com`. Used by `models/lite_client.py` and `models/sonic_client.py` for all model inference.
- **Default:** None — **required for model clients.**
- **Local dev:** Get from [api.nova.amazon.com](https://api.nova.amazon.com). Set in `.env`.
- **AWS deployment:** Not used when migrated to Bedrock. Use `AWS_BEARER_TOKEN_BEDROCK` instead.

### `AWS_BEARER_TOKEN_BEDROCK`
- **What it does:** Bearer token for direct Bedrock API access. When set, model clients use boto3 Bedrock instead of the Nova API.
- **Default:** None (uses Nova API key instead)
- **Local dev:** Not needed if using Nova API.
- **AWS deployment:** Set for production Bedrock access with higher rate limits.

---

## Pulling All Secrets at Once (AWS deployment)

If Manav has deployed the infra stack, you can populate your `.env` from Secrets Manager in one pass:

```bash
# Example helper — adapt secret IDs to match what the CDK stack created
for secret in redis-url database-url opensearch-endpoint api-key; do
  echo "$(echo $secret | tr '-' '_' | tr '[:lower:]' '[:upper:]')=$(aws secretsmanager get-secret-value \
    --secret-id mission-control/$secret \
    --query SecretString \
    --output text)"
done >> .env
```

Ask Bharath or check the CDK stack outputs for the exact secret IDs.
