-- Mission Control (Dispatch) — Postgres Schema
-- Run automatically by Docker Compose on first container start.
-- Run manually in AWS RDS: psql $DATABASE_URL -f infra/init.sql

-- ── Extensions ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Enums ─────────────────────────────────────────────────────────────────────
DO $$ BEGIN
    CREATE TYPE mission_status AS ENUM (
        'PENDING',
        'ACTIVE',
        'SYNTHESIZING',
        'COMPLETE',
        'FAILED'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE task_status AS ENUM (
        'PENDING',
        'ASSIGNED',
        'IN_PROGRESS',
        'DONE',
        'CANCELLED'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE agent_type AS ENUM (
        'OFFICIAL_SITE',
        'NEWS_BLOG',
        'REDDIT_HN',
        'GITHUB',
        'FINANCIAL',
        'RECENT_NEWS'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── missions ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS missions (
    id                    UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    objective             TEXT          NOT NULL,
    status                mission_status NOT NULL DEFAULT 'PENDING',
    task_graph            JSONB,                          -- serialised TaskNode DAG
    agent_ids             TEXT[]        NOT NULL DEFAULT '{}',
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    briefing              TEXT,                           -- final synthesised text
    briefing_audio_s3_key TEXT,                          -- S3 key for spoken briefing
    user_id               TEXT                           -- optional; multi-tenant future
);

-- Auto-update updated_at on every row change
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS missions_updated_at ON missions;
CREATE TRIGGER missions_updated_at
    BEFORE UPDATE ON missions
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- ── tasks ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id                UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id        UUID        NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    description       TEXT        NOT NULL,
    agent_type        agent_type  NOT NULL,
    status            task_status NOT NULL DEFAULT 'PENDING',
    dependencies      UUID[]      NOT NULL DEFAULT '{}',  -- task IDs that must be DONE first
    assigned_agent_id TEXT,                               -- e.g. "agent_2"
    priority          INTEGER     NOT NULL DEFAULT 5,     -- higher = sooner assignment
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_mission_id
    ON tasks(mission_id);

CREATE INDEX IF NOT EXISTS idx_tasks_mission_status
    ON tasks(mission_id, status);

-- ── evidence ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evidence (
    id                UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id        UUID        NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    agent_id          TEXT        NOT NULL,               -- e.g. "agent_2"
    claim             TEXT        NOT NULL,               -- short factual claim
    summary           TEXT        NOT NULL,               -- 1–2 sentence summary
    source_url        TEXT        NOT NULL,
    snippet           TEXT        NOT NULL,               -- raw extracted text
    screenshot_s3_key TEXT,                              -- S3 key for PNG screenshot
    confidence        FLOAT       NOT NULL DEFAULT 0.8,  -- 0.0–1.0
    novelty           FLOAT       NOT NULL DEFAULT 1.0,  -- 0.0–1.0; stub until Task 7
    theme             TEXT,                               -- cluster label (Task 7.4)
    embedding_id      TEXT,                              -- vector store document ID (Task 7.2)
    timestamp         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_mission_id
    ON evidence(mission_id);

CREATE INDEX IF NOT EXISTS idx_evidence_mission_timestamp
    ON evidence(mission_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_evidence_mission_theme
    ON evidence(mission_id, theme)
    WHERE theme IS NOT NULL;
