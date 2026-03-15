# Logging Standard

## Overview

Mission Control uses [structlog](https://www.structlog.org/) for structured JSON logging. All backend services emit logs in a consistent format with correlation IDs for filtering in CloudWatch or local development.

## Configuration

Logging is configured at application startup in `backend/logging_config.py`:

- **Production** (`DEMO_MODE=false`): JSON output to stdout
- **Development** (`DEMO_MODE=true`): Colored console output

Log level is controlled by the `LOG_LEVEL` environment variable (default: `INFO`).

## Context Variables

Every log entry can include correlation IDs bound via `structlog.contextvars`:

| Field | Type | Description |
|-------|------|-------------|
| `mission_id` | UUID string | Active mission being processed |
| `agent_id` | string | Agent executing the task (e.g., `agent_0`) |
| `request_id` | UUID string | HTTP request correlation ID |
| `evidence_id` | UUID string | Evidence record being processed |

### Binding Context

```python
from logging_config import bind_mission_context, get_logger

logger = get_logger(__name__)

# Bind at request/task start
bind_mission_context(mission_id="abc-123", agent_id="agent_0")

# All subsequent logs include mission_id and agent_id
logger.info("evidence_ingested", claim="Sequoia led $60M round", confidence=0.91)
```

## Log Events

Standard event names used across the system:

| Event | Level | Service | Description |
|-------|-------|---------|-------------|
| `mission_start` | INFO | Orchestrator | New mission created |
| `mission_status_change` | INFO | Orchestrator | State transition |
| `agent_assigned` | INFO | Pool | Agent claimed for task |
| `agent_heartbeat_missed` | WARNING | Watchdog | Heartbeat TTL expired |
| `evidence_ingested` | INFO | Evidence | New evidence stored |
| `evidence_dlq_push` | WARNING | DLQ | Evidence failed, queued for retry |
| `synthesis_start` | INFO | Synthesis | Briefing generation started |
| `mission_complete` | INFO | Orchestrator | Mission finished |
| `error` | ERROR | Any | Unhandled exception |

## Output Format

### JSON (Production)

```json
{
  "event": "evidence_ingested",
  "level": "info",
  "logger": "evidence.router",
  "timestamp": "2026-03-15T20:30:00.000Z",
  "mission_id": "abc-123",
  "agent_id": "agent_0",
  "claim": "Sequoia led $60M round"
}
```

### Console (Development)

```
2026-03-15 20:30:00 [info     ] evidence_ingested    [evidence.router] mission_id=abc-123 agent_id=agent_0
```

## CloudWatch Queries

```
# Filter by mission
filter @message like /abc-123/

# All errors
filter level = "error"

# Agent timeouts
filter event = "agent_heartbeat_missed"
```

## Privacy

- **Never log** raw user speech audio or full transcript text at INFO level
- Evidence claims may be logged at INFO (they are derived, not PII)
- Use DEBUG level for full request/response payloads during development
