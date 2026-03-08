# Mission Control — Tasks for Rahil Singhi

**Role:** Evidence Layer, Vector Intelligence & Synthesis  
**GitHub:** [rahilsinghi](https://github.com/rahilsinghi)  
**LinkedIn:** [rahilsinghi27](https://www.linkedin.com/in/rahilsinghi27/)  
**Background:** Built MarketPulse-AI (real-time RAG on financial news streams), beads (memory upgrade for coding agents), Career-Datacenter (Python), agentic system projects. Strong in Python, RAG pipelines, financial data, AI/ML.

---

## Implementation Status

**Last updated:** March 2026

| Task | Status | Notes |
|------|--------|-------|
| 6.1 Evidence Schema + Ingest API | ⏳ Pending | Depends on Manav's Postgres (2.3) and Redis (2.2) |
| 6.2 Screenshot S3 Upload | ⏳ Pending | Depends on 6.1 and Manav's S3 bucket (2.4) |
| 6.3 Confidence + Novelty Scoring | ⏳ Pending | Depends on 6.1; novelty needs Phase 7.2 |
| 6.4 Evidence List API | ⏳ Pending | Depends on 6.1 — unblocks Sariya's Evidence Board |
| 7.1 Embedding Client | ⏳ Pending | Coordinate with Manav on dimension before he creates OpenSearch index (2.5) |
| 7.2 Embedding Pipeline | ⏳ Pending | Depends on 7.1, 6.1, Manav's OpenSearch (2.5) |
| 7.3 Semantic Clustering | ⏳ Pending | Depends on 7.2 |
| 7.4 Theme Classification | ⏳ Pending | Depends on 7.3; needs `models/lite_client.py` from Manav (4.4) |
| 7.5 Contradiction Detection | ⏳ Pending | Depends on 7.2, 4.3 |
| 10.4 Agent Reallocation Triggers | ⏳ Pending | Depends on 4.5, 5.5 |
| 10.5 Mission Stopping Criteria | ⏳ Pending | Depends on 4.5, 4.3 |
| 11.4 Agent Result Aggregation | ⏳ Pending | Depends on 5.4, 6.1, 4.5 |
| 12.1 Clustering + Cluster Labels | ⏳ Pending | Depends on 7.3, 7.4 |
| 12.2 Final Intelligence Synthesis | ⏳ Pending | Depends on 4.3, 7.4, 7.5 |
| 12.3 Spoken Briefing via Sonic | ⏳ Pending | Depends on Chinmay's gateway (3.3) and 12.2 |

### What You Need First

The TypeScript types for your evidence schema are already defined in `frontend/src/types/api.ts` — use these as the source of truth when writing your Pydantic models in `backend/evidence/schemas.py` so field names stay in sync with Sariya's UI.

**Your critical path:** 7.1 (embedding client) → tell Manav the `EMBEDDING_DIMENSION` constant → he creates the OpenSearch index → then 6.1 → 7.2 can run in parallel.

**Share with Manav early:** `EMBEDDING_DIMENSION` from `models/embedding_client.py` — he needs it before provisioning OpenSearch (Task 2.5).

**Share with Chinmay early:** The `POST /internal/deliver-briefing` contract (Task 12.3) — he builds against this in his voice gateway (Task 3.3).

---

## Why These Tasks

Your MarketPulse-AI project is essentially a proof of concept for everything Mission Control needs in its evidence layer: real-time data ingestion, RAG-based retrieval, embedding + ranking, and confidence scoring. You own the full data path from "agent emits a finding" through "embedding stored in vector index" through "final intelligence synthesis." You also own the planning-layer logic for reallocation and stopping, and the agent command aggregation path.

---

## Task Summary

| Task | Phase | Description | Depends On | Status |
|------|-------|-------------|------------|--------|
| 6.1 | Evidence | Evidence schema, storage, ingest API | 2.3 | ⏳ Pending |
| 6.2 | Evidence | Screenshot capture + S3 upload | 6.1, 2.4 | ⏳ Pending |
| 6.3 | Evidence | Confidence + novelty scoring | 6.1, Phase 7 | ⏳ Pending |
| 6.4 | Evidence | Evidence list API (paginated, theme filter) | 6.1 | ⏳ Pending |
| 7.1 | Vectors | Nova Multimodal Embeddings client | Phase 1, Bedrock access | ⏳ Pending |
| 7.2 | Vectors | Embedding pipeline on evidence ingest | 7.1, 6.1, 2.5 | ⏳ Pending |
| 7.3 | Vectors | Semantic clustering endpoint | 7.2 | ⏳ Pending |
| 7.4 | Vectors | Theme classification (Nova Lite) | 7.3 | ⏳ Pending |
| 7.5 | Vectors | Contradiction detection | 7.2, 4.3 | ⏳ Pending |
| 10.4 | Planning | Agent reallocation triggers | 4.5, 5.5 | ⏳ Pending |
| 10.5 | Planning | Mission stopping criteria | 4.5, 4.3 | ⏳ Pending |
| 11.4 | Orchestration | Agent result aggregation | 5.4, 6.1, 4.5 | ⏳ Pending |
| 12.1 | Synthesis | Clustering algorithm + cluster labels | 7.3, 7.4 | ⏳ Pending |
| 12.2 | Synthesis | Final intelligence synthesis prompt | 4.3, 7.4, 7.5 | ⏳ Pending |
| 12.3 | Synthesis | Spoken briefing via Sonic | 3.3, 12.2 | ⏳ Pending |

**Total: 15 tasks — 0 Done, 15 Pending**

---

## Coordination Map

| You need from | What |
|---------------|------|
| **Manav** | Postgres (Task 2.3), S3 bucket (Task 2.4), OpenSearch endpoint (Task 2.5), Redis (Task 2.2), orchestrator `build_context_packet` (Task 4.3) |
| **Chinmay** | Voice Gateway `deliver_final_briefing` endpoint (Task 3.3) for Task 12.3; agent heartbeat and lifecycle (Task 5.5) for Task 11.4 |
| **Bharath** | `S3_BUCKET_EVIDENCE`, `OPENSEARCH_ENDPOINT`, `BEDROCK_MODEL_EMBEDDING` env vars from Task 1.3 |
| **Sariya** | Presigned screenshot URLs (Task 6.2) consumed by Evidence Board (Task 8.5) |

---

## Full Task Details

---

### Task 6.1 — Evidence Object Schema and Storage

**Description:** Implement the `EvidenceRecord` Pydantic schema, the Postgres persistence layer, and the `POST /evidence` ingest endpoint. This is the primary write path for all browser agents.

**Technical implementation notes:**
- File: `backend/evidence/schemas.py`. Pydantic model matching `tasks.md` schema:
  ```python
  from pydantic import BaseModel, HttpUrl
  from uuid import UUID
  from datetime import datetime

  class EvidenceIngest(BaseModel):
      mission_id: UUID
      agent_id: str
      claim: str
      summary: str
      source_url: HttpUrl
      snippet: str
      screenshot_base64: str | None = None
      confidence: float = 0.8
      novelty: float = 1.0

  class EvidenceRecord(EvidenceIngest):
      id: UUID
      screenshot_s3_key: str | None = None
      theme: str | None = None
      embedding_id: str | None = None
      timestamp: datetime
  ```
- File: `backend/evidence/repository.py`. Async `asyncpg` functions: `create_evidence(payload) -> EvidenceRecord`, `get_evidence_by_mission(mission_id, limit, offset, theme) -> list[EvidenceRecord]`, `update_evidence_theme(id, theme)`, `update_evidence_embedding(id, embedding_id)`.
- File: `backend/routers/evidence.py`. `POST /evidence`: validate `EvidenceIngest`, call `create_evidence`, kick off async pipeline (screenshot upload Task 6.2, embedding Task 7.2), publish `EVIDENCE_FOUND` to Redis (via Manav's `publish_agent_finding`), return `{ "id": UUID }`.
- Default `confidence=0.8`, `novelty=1.0` (full novelty updated after embedding in Task 6.3).

**Dependencies:** Manav's Postgres (Task 2.3); Manav's Redis (Task 2.2) for publish.

**Expected output:** `POST /evidence` with valid payload returns 200 with new UUID; row visible in Postgres; `EVIDENCE_FOUND` message appears on Redis channel.

**Subtasks:**
- 6.1.1 Pydantic schemas.
- 6.1.2 Postgres repository functions.
- 6.1.3 FastAPI router with background task dispatch.
- 6.1.4 Unit tests with mock DB and mock Redis publish.

---

### Task 6.2 — Screenshot Capture and S3 Upload

**Description:** When evidence arrives with a `screenshot_base64` field, decode it and upload to S3. Set `screenshot_s3_key` on the evidence record. Generate presigned GET URLs for the frontend.

**Technical implementation notes:**
- File: `backend/evidence/screenshot.py`.
- Function: `async def upload_screenshot(evidence_id: UUID, mission_id: UUID, base64_data: str) -> str`:
  ```python
  import base64, boto3

  async def upload_screenshot(evidence_id, mission_id, base64_data):
      s3 = boto3.client("s3")
      key = f"evidence/{mission_id}/{evidence_id}.png"
      image_bytes = base64.b64decode(base64_data)
      s3.put_object(
          Bucket=settings.S3_BUCKET_EVIDENCE,
          Key=key,
          Body=image_bytes,
          ContentType="image/png"
      )
      return key
  ```
- Function: `def get_screenshot_url(key: str) -> str`: generates `s3.generate_presigned_url("get_object", ...)` with `ExpiresIn=3600`. Returns URL to include in `EvidenceRecord.screenshot_url` (virtual field, not stored).
- After upload, call `db.update_evidence_screenshot_key(evidence_id, key)`.
- Run as a background task after `POST /evidence` returns (do not block the response).

**Dependencies:** Task 6.1, Manav's S3 bucket (Task 2.4).

**Expected output:** Evidence with screenshot has `screenshot_s3_key` in DB; calling `GET /missions/{id}/evidence` returns a `screenshot_url` presigned link that loads in browser.

---

### Task 6.3 — Confidence and Novelty Scoring

**Description:** Assign `confidence` based on source heuristics and `novelty` based on cosine similarity vs existing evidence for the same mission. Novelty prevents the context packet from flooding Nova Lite with redundant findings.

**Technical implementation notes:**
- File: `backend/evidence/scoring.py`.
- **Confidence heuristic** (run synchronously on ingest):
  ```python
  OFFICIAL_DOMAINS = {"sequoiacap.com", "crunchbase.com", "pitchbook.com"}

  def compute_confidence(source_url: str, snippet: str) -> float:
      domain = urlparse(source_url).netloc.replace("www.", "")
      base = 0.9 if domain in OFFICIAL_DOMAINS else 0.7
      # longer snippet = slightly more confident
      length_bonus = min(0.1, len(snippet) / 5000)
      return round(min(1.0, base + length_bonus), 3)
  ```
- **Novelty** (run after embedding is stored in Phase 7.2):
  ```python
  async def compute_novelty(evidence_id, mission_id, opensearch_client) -> float:
      # k-NN search excluding the current doc
      results = await opensearch_client.search(
          index="evidence_vectors",
          body={"query": {"knn": {"embedding": {"vector": current_vec, "k": 5}}},
                "filter": {"term": {"mission_id": str(mission_id)}}}
      )
      if not results["hits"]["hits"]:
          return 1.0
      max_sim = max(h["_score"] for h in results["hits"]["hits"]
                    if h["_id"] != str(evidence_id))
      return round(max(0.0, 1.0 - max_sim), 3)
  ```
- After computing novelty, call `db.update_evidence_novelty(evidence_id, novelty)`.
- Stub novelty to 1.0 until Phase 7.2 is complete; add a TODO comment.

**Dependencies:** Task 6.1 (must run after evidence is stored); Phase 7.2 for real novelty.

**Expected output:** Every evidence record has `confidence` and `novelty` fields; context packet can rank findings by `confidence * novelty`.

---

### Task 6.4 — Evidence List API

**Description:** `GET /missions/{id}/evidence` — paginated list of evidence records for a mission, with optional theme filter. Used by the War Room Evidence Board and the orchestrator context builder.

**Technical implementation notes:**
- Router: add to `backend/routers/evidence.py` or `backend/routers/missions.py`.
- Query params: `limit: int = 20` (max 100), `offset: int = 0`, `theme: str | None = None`.
- SQL:
  ```sql
  SELECT * FROM evidence
  WHERE mission_id = $1 AND ($2::text IS NULL OR theme = $2)
  ORDER BY timestamp DESC
  LIMIT $3 OFFSET $4;
  ```
- Response: `{ "items": EvidenceRecord[], "total": int, "limit": int, "offset": int }`.
- Include `screenshot_url` (presigned, generated on-the-fly) in each item if `screenshot_s3_key` is set.

**Dependencies:** Task 6.1.

**Expected output:** Frontend can call `GET /missions/{id}/evidence?limit=20` and receive paginated evidence cards; theme filter reduces results correctly.

---

### Task 7.1 — Nova Multimodal Embeddings Client

**Description:** Implement `models/embedding_client.py` that calls Amazon Bedrock Nova Multimodal Embeddings. Accepts text (required) and optional image bytes (screenshot). Returns a normalized float vector.

**Technical implementation notes:**
- File: `models/embedding_client.py`.
- Check Bedrock docs for Nova Multimodal Embedding model ID (e.g. `amazon.titan-embed-image-v1` or the Nova equivalent). Record exact model ID and output dimension in `models/embedding_client.py` as constants.
  ```python
  EMBEDDING_MODEL_ID = "amazon.nova-pro-v1:0"  # update with correct ID
  EMBEDDING_DIMENSION = 1024                       # update from Bedrock docs

  async def embed_evidence(text: str, image_bytes: bytes | None = None) -> list[float]:
      client = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)
      body = {"inputText": text}
      if image_bytes:
          body["inputImage"] = base64.b64encode(image_bytes).decode()
      response = client.invoke_model(
          modelId=EMBEDDING_MODEL_ID,
          body=json.dumps(body),
          contentType="application/json",
          accept="application/json"
      )
      result = json.loads(response["body"].read())
      return result["embedding"]  # adjust key per actual API response shape
  ```
- Normalize vector (L2 normalize) before returning to ensure cosine similarity works correctly in OpenSearch.
- Export `EMBEDDING_DIMENSION` so Manav can use it when creating the OpenSearch index (Task 2.5) — coordinate early.

**Dependencies:** Phase 1; Bedrock access with `bedrock:InvokeModel` permission on embedding model.

**Expected output:** `embed_evidence("test text") -> list[float]` with length `EMBEDDING_DIMENSION`; unit test with `mock_boto3` verifies shape and that L2 norm ≈ 1.0.

---

### Task 7.2 — Embedding Pipeline on Evidence Ingest

**Description:** After a new evidence record is stored (Task 6.1), compute its embedding and index it into OpenSearch Serverless. Store the OpenSearch document ID as `embedding_id` on the evidence record.

**Technical implementation notes:**
- File: `backend/evidence/embedding_pipeline.py`.
- Triggered as `asyncio.create_task` from `POST /evidence` handler (non-blocking):
  ```python
  async def run_embedding_pipeline(evidence: EvidenceRecord, db, opensearch):
      text = f"{evidence.claim}. {evidence.summary}. {evidence.snippet[:500]}"
      image_bytes = None
      if evidence.screenshot_s3_key:
          image_bytes = await s3_get_object(evidence.screenshot_s3_key)
      vector = await embed_evidence(text, image_bytes)
      doc = {
          "embedding": vector,
          "mission_id": str(evidence.mission_id),
          "evidence_id": str(evidence.id),
          "text_summary": text
      }
      response = opensearch.index(index="evidence_vectors", body=doc)
      embedding_id = response["_id"]
      await db.update_evidence_embedding(evidence.id, embedding_id)
      # Now compute novelty with the vector we just got
      novelty = await compute_novelty(evidence.id, evidence.mission_id, opensearch, vector)
      await db.update_evidence_novelty(evidence.id, novelty)
  ```
- Error handling: log failures; evidence still usable without embedding. Retry once after 5 s.
- OpenSearch client: use `opensearch-py` (async) with AWS4Auth for SigV4 signing.

**Dependencies:** Task 7.1, 6.1, Manav's OpenSearch (Task 2.5).

**Expected output:** Every new evidence record gets an `embedding_id` within ~3 s of ingest; searchable in OpenSearch via k-NN.

---

### Task 7.3 — Semantic Clustering Endpoint

**Description:** Given `mission_id`, fetch all evidence vectors from OpenSearch, run HDBSCAN clustering, and return cluster assignments. Used by Task 7.4 (theme labelling) and Task 12.1 (synthesis).

**Technical implementation notes:**
- File: `backend/evidence/clustering.py`.
- Function: `async def cluster_evidence(mission_id: UUID, opensearch) -> list[ClusterGroup]`:
  1. Scroll all docs from `evidence_vectors` where `mission_id == mission_id`. Collect vectors + evidence_ids.
  2. Run `hdbscan.HDBSCAN(min_cluster_size=2, metric="euclidean").fit(np.array(vectors))`.
  3. Group evidence_ids by label (label == -1 means noise/unclustered).
  4. Return `list[{ "cluster_id": int, "evidence_ids": list[UUID] }]`.
- Optional REST endpoint: `GET /missions/{id}/clusters` for debugging (not required by frontend).
- Install: `hdbscan>=0.8`, `numpy>=1.26` in `pyproject.toml`.

**Dependencies:** Task 7.2 (vectors must exist in OpenSearch).

**Expected output:** For a mission with 10+ evidence items, clusters are computed with 2–4 groups; no evidence is permanently lost (noise items assigned individually).

---

### Task 7.4 — Theme Classification

**Description:** For each cluster from Task 7.3, call Nova Lite to assign a concise theme label (e.g. "Recent investments", "Founder complaints"). Store theme on each evidence record in the cluster.

**Technical implementation notes:**
- File: `backend/evidence/theme_labeler.py`.
- For each cluster:
  1. Fetch evidence summaries from DB for the `evidence_ids` in the cluster.
  2. Build prompt: `"Label this cluster of research findings with a short phrase (3-6 words). Findings:\n" + "\n".join(summaries[:5])`.
  3. Call Nova Lite (`models/lite_client.py`). Extract text from response. Strip quotes.
  4. Update each `evidence.theme = label` in DB batch update.
- Run after `cluster_evidence` completes; can run at each planning cycle or once at synthesis.
- Schedule: call from planning loop (Task 4.5) every 15 s if new evidence arrived since last run.

**Dependencies:** Task 7.3; Nova Lite client from Manav (Task 4.4 creates `lite_client.py`).

**Expected output:** All evidence records have a `theme` field; `GET /missions/{id}/evidence?theme=Founder+complaints` filters correctly; War Room Evidence Board can group by theme.

---

### Task 7.5 — Contradiction Detection

**Description:** Identify pairs of evidence that contradict each other. Populate `MissionContextPacket.contradictions` so Nova Lite can surface them in planning and the War Room can display conflict flags.

**Technical implementation notes:**
- File: `backend/evidence/contradictions.py`.
- Algorithm (choose one or combine):
  - **Option A (embedding-based):** For each evidence item, find the k=3 nearest neighbors in OpenSearch. For each neighbor pair, call Nova Lite with both `claim` fields: `"Do these two claims contradict each other? Answer yes or no and explain briefly."`. If "yes", add to contradictions.
  - **Option B (LLM scan):** When evidence_count > 5, send top 10 evidence claims to Lite in one call: `"Identify any contradicting pairs. Return JSON: [{ \"a\": <claim>, \"b\": <claim>, \"reason\": <str> }]"`.
- Return: `list[{ "evidence_id_a": UUID, "evidence_id_b": UUID, "description": str }]`.
- Cache result in Redis key `mission:{id}:contradictions` with TTL 30 s (avoids re-running every context build).
- Called by context builder (Manav's Task 4.3) via import or internal HTTP call.

**Dependencies:** Task 7.2; Manav's context builder (Task 4.3).

**Expected output:** Contradictions list included in `MissionContextPacket`; demo scenario shows at least one detected contradiction.

---

### Task 10.4 — Agent Reallocation Triggers

**Description:** Define the conditions under which the orchestrator should redirect a running agent to a different objective. Implement the trigger detection inside the planning loop.

**Technical implementation notes:**
- File: `backend/orchestrator/reallocation.py`. Function: `async def detect_reallocation_opportunities(context_packet, db) -> list[RedirectAction]`.
- Triggers:
  1. **Low-yield agent:** if an agent has been BROWSING for > 20 s with no evidence emitted, redirect it to the next highest-priority PENDING task.
  2. **Contradiction priority:** if `contradictions` list is non-empty and no agent is assigned to investigate, redirect one idle agent to a `REDDIT_HN` or `NEWS_BLOG` search targeting the contradiction.
  3. **Coverage gap:** if a particular theme has < 2 evidence items after 15 s, create an implicit redirect to gather more on that topic.
  4. **Nova Lite override:** planning loop already asks Lite for `redirect` actions; treat those as highest priority.
- Return list of `RedirectAction` (`{ agent_id, new_objective }`); planning loop dispatches them as `REDIRECT` commands.

**Dependencies:** Task 4.5, Task 5.5 (heartbeat gives last-seen evidence count per agent).

**Expected output:** Planning loop calls `detect_reallocation_opportunities` each cycle; at least one agent redirect visible in demo timeline.

---

### Task 10.5 — Mission Stopping Criteria

**Description:** Define and implement the conditions under which the orchestrator transitions the mission from ACTIVE to SYNTHESIZING.

**Technical implementation notes:**
- File: `backend/orchestrator/stopping.py`. Function: `async def should_stop(mission_id, context_packet, db) -> bool`.
- Criteria (any one triggers stop):
  1. **Time budget:** `context_packet.time_elapsed_sec >= 40` (leaves 5 s buffer before 45 s briefing target).
  2. **Coverage threshold:** every `open_question` (PENDING or ASSIGNED task) has `evidence_count_for_theme >= 3`.
  3. **Nova Lite vote:** planning loop response includes `{ "action": "synthesize" }`.
  4. **All tasks DONE:** no tasks in PENDING or ASSIGNED state remain.
- If stopping: call `transition(mission_id, SYNTHESIZING)`, cancel planning loop, trigger synthesis (Task 12.2).
- Check at the end of every planning cycle.

**Dependencies:** Task 4.5, Task 4.3 (context packet provides counts and elapsed time).

**Expected output:** Mission reliably transitions to SYNTHESIZING before the 45 s latency deadline; no mission hangs in ACTIVE forever.

---

### Task 11.4 — Agent Result Aggregation

**Description:** When an agent completes a task (via a `task_complete` event or evidence threshold), update task status to DONE, mark agent as IDLE, and ensure the orchestrator's next planning cycle sees the updated state.

**Technical implementation notes:**
- File: `backend/orchestrator/aggregator.py`.
- Listen on Redis channel `agent:{id}:findings` for a completion signal (either `type == "TASK_COMPLETE"` or evidence count for that task exceeds `settings.TASK_EVIDENCE_THRESHOLD` — default 3).
- On completion:
  1. Set `tasks.status = DONE` in Postgres.
  2. Set `agent_id → { status: IDLE, task_id: null }` in Redis hash.
  3. Publish `TIMELINE_EVENT` `agent_completed` to `mission:{id}:events`.
  4. Trigger next planning cycle immediately (instead of waiting for the 10 s timer) by posting to a Redis key or asyncio event.
- Handle timeout: if agent has not completed after `settings.TASK_TIMEOUT_SEC = 60`, mark DONE anyway and IDLE the agent (avoids blocking synthesis).

**Dependencies:** Task 5.4 (agents emit findings), Task 6.1 (evidence stored so count is queryable), Task 4.5.

**Expected output:** Task flips to DONE within 2 s of last evidence; agent is available for reassignment; `GET /missions/{id}/tasks` shows correct status.

---

### Task 12.1 — Clustering Algorithm and Cluster Labels

**Description:** Run the full clustering + labelling pipeline at synthesis time: fetch all mission evidence vectors, cluster with HDBSCAN, label with Nova Lite, and persist theme on all evidence records. This is the final pre-synthesis preparation.

**Technical implementation notes:**
- Reuse `cluster_evidence` (Task 7.3) and `label_cluster` (Task 7.4).
- File: `backend/synthesis/pre_synthesis.py`.
- Function: `async def prepare_evidence_clusters(mission_id, db, opensearch) -> list[ClusterSummary]`:
  1. Call `cluster_evidence(mission_id, opensearch)` — get cluster groups.
  2. For each cluster, call `label_cluster(evidence_ids, db)` — get theme label.
  3. Batch-update `evidence.theme` for all evidence in each cluster.
  4. Return `list[{ "theme": str, "evidence_count": int, "top_claims": list[str] }]` — the `ClusterSummary` used by synthesis prompt.
- Call this function as the first step when mission transitions to SYNTHESIZING.

**Dependencies:** Task 7.3, 7.4.

**Expected output:** All evidence records have themes; synthesis receives a `ClusterSummary[]` input ready for briefing generation.

---

### Task 12.2 — Final Intelligence Synthesis Prompt

**Description:** Call Nova Lite with the mission objective and themed evidence summaries to generate a structured intelligence briefing. Store it in `mission.briefing` and set status to COMPLETE.

**Technical implementation notes:**
- File: `backend/synthesis/briefing.py`.
- Input: `mission_id`, `cluster_summaries: list[ClusterSummary]`, `contradictions: list`.
- Build prompt:
  ```
  System: You are an intelligence analyst. Produce a structured briefing.
  
  Mission: {objective}
  
  Evidence by Theme:
  {for each cluster: "## {theme}\n" + top 3 claims}
  
  Contradictions detected:
  {contradictions or "None"}
  
  Output a briefing with:
  1. Executive Summary (2-3 sentences)
  2. Key Findings by Theme (bullet points)
  3. Contradictions to Note
  4. Strategic Recommendations (2-3 bullets)
  
  Keep it tight. This will be spoken aloud. Avoid bullet nesting.
  ```
- Call Nova Lite (non-streaming). Parse text response. Store in `db.update_mission_briefing(mission_id, briefing_text)`.
- Transition mission to COMPLETE via Manav's state machine.
- Emit `MISSION_STATUS` event to Redis.

**Dependencies:** Task 4.3 (context packet for contradictions), Task 7.4 (themes), Task 7.5 (contradictions).

**Expected output:** `mission.briefing` populated with a coherent, themed briefing; `mission.status = COMPLETE`; demo briefing covers all four Sequoia topics in < 300 words.

---

### Task 12.3 — Spoken Briefing via Sonic

**Description:** After synthesis (Task 12.2), trigger Sonic to deliver the briefing as audio to the user. The `deliver_final_briefing` tool on the Sonic side calls back to this path.

**Technical implementation notes:**
- File: `backend/synthesis/spoken_briefing.py`.
- When `POST /missions/{id}` or planning loop triggers synthesis completion, call Sonic gateway with `deliver_final_briefing(mission_id, briefing_text)` tool result injection.
- Coordinate with Chinmay: the Voice Gateway (Task 3.3) handles the Sonic streaming; you provide the `briefing_text` as the tool return value.
- API contract between you and Chinmay: `POST /internal/deliver-briefing` with body `{ "mission_id": UUID, "briefing_text": str }`. Gateway responds with 202; briefing audio streamed to client via WebSocket `BRIEFING_CHUNK` events.
- Optionally store audio in S3 (gateway puts audio bytes to S3; updates `mission.briefing_audio_s3_key`) for replay.

**Dependencies:** Chinmay's Task 3.3 (Voice Gateway WebSocket); Task 12.2 (briefing text ready).

**Expected output:** After mission reaches COMPLETE, user hears the briefing spoken by Sonic within 5 s; `BRIEFING_CHUNK` events visible in browser dev tools.

---

## Quick Reference — Files You Own

```
backend/evidence/
  schemas.py
  repository.py
  screenshot.py
  scoring.py
  embedding_pipeline.py
  clustering.py
  theme_labeler.py
  contradictions.py
backend/routers/evidence.py
backend/orchestrator/
  reallocation.py
  stopping.py
  aggregator.py
backend/synthesis/
  pre_synthesis.py
  briefing.py
  spoken_briefing.py
models/embedding_client.py
```
