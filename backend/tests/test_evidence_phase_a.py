"""Integration tests for Phase A evidence features.

Tests cover:
  - Task 7.1: Embedding client (mock + live Bedrock)
  - Task 6.2: Screenshot S3 upload (mock + MinIO)
  - Task 6.3: Confidence scoring + novelty stub
  - Updated evidence router with screenshot + confidence wiring

All tests use mocks by default. Live API tests are marked with
@pytest.mark.live and require real credentials.
"""

from __future__ import annotations

import base64
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from main import app

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_evidence(
    *,
    id: str | None = None,
    mission_id: str | None = None,
    agent_id: str = "agent_0",
    claim: str = "Sequoia invested in AI startup",
    summary: str = "Major AI investment by Sequoia",
    source_url: str = "https://sequoiacap.com/investments",
    snippet: str = "According to sources, Sequoia Capital has invested $100M...",
    confidence: float = 0.9,
    novelty: float = 1.0,
    theme: str | None = None,
    screenshot_s3_key: str | None = None,
    embedding_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": id or str(uuid.uuid4()),
        "mission_id": mission_id or str(uuid.uuid4()),
        "agent_id": agent_id,
        "claim": claim,
        "summary": summary,
        "source_url": source_url,
        "snippet": snippet,
        "confidence": confidence,
        "novelty": novelty,
        "theme": theme,
        "screenshot_s3_key": screenshot_s3_key,
        "embedding_id": embedding_id,
        "timestamp": datetime.now(timezone.utc),
    }


def _as_record(d: dict) -> MagicMock:
    """Mock an asyncpg.Record."""
    rec = MagicMock()
    rec.__iter__ = lambda self: iter(d.items())
    rec.items = lambda: d.items()
    rec.keys = lambda: d.keys()
    rec.values = lambda: d.values()
    rec.get = d.get
    rec.__getitem__ = lambda self, k: d[k]
    return rec


def _mock_app_state(evidence: dict | None = None, evidence_list: list | None = None):
    """Return a mock app.state for the test client."""
    evidence = evidence or _make_evidence()
    evidence_list = evidence_list or []

    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=_as_record(evidence))
    pool.fetch = AsyncMock(return_value=[_as_record(e) for e in evidence_list])
    pool.execute = AsyncMock()

    redis = AsyncMock()
    redis.publish = AsyncMock(return_value=1)

    state = MagicMock()
    state.db = pool
    state.redis = redis
    return state


# ===========================================================================
# Task 6.3 — Confidence scoring
# ===========================================================================


class TestConfidenceScoring:
    """Test the compute_confidence heuristic."""

    def test_official_domain_high_base(self):
        from evidence.scoring import compute_confidence

        score = compute_confidence("https://sequoiacap.com/about", "short snippet")
        assert score >= 0.9
        assert score <= 1.0

    def test_crunchbase_official(self):
        from evidence.scoring import compute_confidence

        score = compute_confidence("https://www.crunchbase.com/org/test", "data")
        assert score >= 0.9

    def test_unknown_domain_lower_base(self):
        from evidence.scoring import compute_confidence

        score = compute_confidence("https://randomsite.io/page", "short")
        assert 0.7 <= score < 0.9

    def test_longer_snippet_increases_score(self):
        from evidence.scoring import compute_confidence

        short_score = compute_confidence("https://example.com", "x" * 10)
        long_score = compute_confidence("https://example.com", "x" * 3000)
        assert long_score > short_score

    def test_max_score_capped_at_one(self):
        from evidence.scoring import compute_confidence

        score = compute_confidence("https://sequoiacap.com/about", "x" * 10000)
        assert score <= 1.0

    def test_empty_url_handled(self):
        from evidence.scoring import compute_confidence

        score = compute_confidence("", "some text")
        assert 0.0 <= score <= 1.0

    def test_invalid_url_handled(self):
        from evidence.scoring import compute_confidence

        score = compute_confidence("not-a-url", "some text")
        assert 0.0 <= score <= 1.0

    def test_precision_three_decimals(self):
        from evidence.scoring import compute_confidence

        score = compute_confidence("https://example.com", "test snippet")
        # Check it's rounded to 3 decimal places
        assert score == round(score, 3)


class TestNoveltyScoring:
    """Test the compute_novelty function (stub mode + future OpenSearch)."""

    @pytest.mark.anyio
    async def test_stub_returns_one_when_no_opensearch(self):
        from evidence.scoring import compute_novelty

        result = await compute_novelty("eid", "mid")
        assert result == 1.0

    @pytest.mark.anyio
    async def test_stub_returns_one_when_no_vector(self):
        from evidence.scoring import compute_novelty

        mock_os = MagicMock()
        result = await compute_novelty("eid", "mid", opensearch_client=mock_os)
        assert result == 1.0

    @pytest.mark.anyio
    async def test_returns_one_when_no_hits(self):
        from evidence.scoring import compute_novelty

        mock_os = AsyncMock()
        mock_os.search = AsyncMock(return_value={"hits": {"hits": []}})
        result = await compute_novelty(
            "eid", "mid", opensearch_client=mock_os, vector=[0.1] * 1024
        )
        assert result == 1.0

    @pytest.mark.anyio
    async def test_novelty_decreases_with_similar_docs(self):
        from evidence.scoring import compute_novelty

        mock_os = AsyncMock()
        mock_os.search = AsyncMock(
            return_value={
                "hits": {
                    "hits": [
                        {"_id": "other_doc", "_score": 0.8},
                    ]
                }
            }
        )
        result = await compute_novelty(
            "eid", "mid", opensearch_client=mock_os, vector=[0.1] * 1024
        )
        assert result == 0.2  # 1.0 - 0.8

    @pytest.mark.anyio
    async def test_own_doc_excluded_from_similarity(self):
        from evidence.scoring import compute_novelty

        mock_os = AsyncMock()
        mock_os.search = AsyncMock(
            return_value={
                "hits": {
                    "hits": [
                        {"_id": "eid", "_score": 0.99},  # self (excluded)
                        {"_id": "other", "_score": 0.3},
                    ]
                }
            }
        )
        result = await compute_novelty(
            "eid", "mid", opensearch_client=mock_os, vector=[0.1] * 1024
        )
        assert result == 0.7  # 1.0 - 0.3 (self excluded)

    @pytest.mark.anyio
    async def test_opensearch_error_returns_one(self):
        from evidence.scoring import compute_novelty

        mock_os = AsyncMock()
        mock_os.search = AsyncMock(side_effect=Exception("connection lost"))
        result = await compute_novelty(
            "eid", "mid", opensearch_client=mock_os, vector=[0.1] * 1024
        )
        assert result == 1.0


# ===========================================================================
# Task 7.1 — Embedding client
# ===========================================================================


class TestEmbeddingClient:
    """Test embedding client with mocked Bedrock API."""

    def test_constants_exported(self):
        from models.embedding_client import EMBEDDING_DIMENSION, EMBEDDING_MODEL_ID

        assert EMBEDDING_DIMENSION == 1024
        assert EMBEDDING_MODEL_ID == "amazon.titan-embed-image-v1"

    def test_l2_normalize(self):
        from models.embedding_client import _l2_normalize

        vec = [3.0, 4.0]
        normed = _l2_normalize(vec)
        norm = math.sqrt(sum(x * x for x in normed))
        assert abs(norm - 1.0) < 1e-6

    def test_l2_normalize_zero_vector(self):
        from models.embedding_client import _l2_normalize

        vec = [0.0, 0.0, 0.0]
        normed = _l2_normalize(vec)
        assert normed == [0.0, 0.0, 0.0]

    def test_missing_token_raises(self):
        from models.embedding_client import EmbeddingClient

        with pytest.raises(ValueError, match="bearer token required"):
            EmbeddingClient(bearer_token="")

    @pytest.mark.anyio
    async def test_embed_text_only(self):
        from models.embedding_client import EMBEDDING_DIMENSION, EmbeddingClient

        fake_vector = [0.1] * EMBEDDING_DIMENSION
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"embedding": fake_vector}

        with patch("models.embedding_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = EmbeddingClient(bearer_token="test-token", region="us-east-1")
            client._client = mock_client
            result = await client.embed("test text")

            assert len(result) == EMBEDDING_DIMENSION
            # Verify L2 normalized
            norm = math.sqrt(sum(x * x for x in result))
            assert abs(norm - 1.0) < 1e-6

    @pytest.mark.anyio
    async def test_embed_with_image(self):
        from models.embedding_client import EMBEDDING_DIMENSION, EmbeddingClient

        fake_vector = [0.2] * EMBEDDING_DIMENSION
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"embedding": fake_vector}

        client = EmbeddingClient(bearer_token="test-token")
        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_response)

        image_bytes = b"\x89PNG\r\n\x1a\nfakeimage"
        result = await client.embed("test with image", image_bytes=image_bytes)

        assert len(result) == EMBEDDING_DIMENSION
        # Verify image was base64-encoded in the request body
        call_args = client._client.post.call_args
        sent_body = json.loads(call_args.kwargs["content"])
        assert "inputImage" in sent_body
        assert sent_body["inputImage"] == base64.b64encode(image_bytes).decode()

    @pytest.mark.anyio
    async def test_embed_evidence_convenience(self):
        from models.embedding_client import EMBEDDING_DIMENSION, EmbeddingClient

        fake_vector = [0.15] * EMBEDDING_DIMENSION
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"embedding": fake_vector}

        client = EmbeddingClient(bearer_token="test-token")
        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.embed_evidence(
            claim="Sequoia invested in AI",
            summary="Major investment",
            snippet="Long snippet text " * 100,
        )
        assert len(result) == EMBEDDING_DIMENSION

        # Verify text was concatenated and snippet truncated
        call_args = client._client.post.call_args
        sent_body = json.loads(call_args.kwargs["content"])
        assert "Sequoia invested in AI" in sent_body["inputText"]
        # Snippet should be truncated to 500 chars
        assert len(sent_body["inputText"]) < 600

    def test_exports_from_package(self):
        from models import EMBEDDING_DIMENSION, EMBEDDING_MODEL_ID, EmbeddingClient

        assert EMBEDDING_DIMENSION == 1024
        assert EMBEDDING_MODEL_ID is not None
        assert EmbeddingClient is not None


# ===========================================================================
# Task 6.2 — Screenshot upload
# ===========================================================================


class TestScreenshotUpload:
    """Test screenshot S3 upload functionality."""

    @pytest.mark.anyio
    async def test_upload_screenshot_calls_s3(self):
        from evidence.screenshot import upload_screenshot

        mock_s3 = MagicMock()
        mock_s3.put_object = MagicMock()

        evidence_id = uuid.uuid4()
        mission_id = uuid.uuid4()
        image_data = base64.b64encode(b"fakepngdata").decode()

        with patch("evidence.screenshot._get_s3_client") as mock_get:
            mock_get.return_value = (mock_s3, "evidence")
            key = await upload_screenshot(evidence_id, mission_id, image_data)

        assert key == f"evidence/{mission_id}/{evidence_id}.png"
        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args.kwargs
        assert call_kwargs["Bucket"] == "evidence"
        assert call_kwargs["Key"] == key
        assert call_kwargs["Body"] == b"fakepngdata"
        assert call_kwargs["ContentType"] == "image/png"

    def test_get_screenshot_url_generates_presigned(self):
        from evidence.screenshot import get_screenshot_url

        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url = MagicMock(
            return_value="https://minio:9000/evidence/key.png?sig=abc"
        )

        with patch("evidence.screenshot._get_s3_client") as mock_get:
            mock_get.return_value = (mock_s3, "evidence")
            url = get_screenshot_url("evidence/mid/eid.png", expires_in=1800)

        assert "key.png" in url
        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "evidence", "Key": "evidence/mid/eid.png"},
            ExpiresIn=1800,
        )


# ===========================================================================
# Router integration — confidence + screenshot wiring
# ===========================================================================


class TestEvidenceRouterPhaseA:
    """Test the updated evidence router with confidence scoring + screenshot."""

    @pytest.mark.anyio
    async def test_ingest_computes_confidence_from_source(self):
        """Confidence should be computed from source_url, not the submitted value."""
        evidence = _make_evidence(
            source_url="https://sequoiacap.com/investments",
            snippet="Sequoia recently invested in...",
        )
        state = _mock_app_state(evidence=evidence)
        app.state = state

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/evidence",
                json={
                    "mission_id": evidence["mission_id"],
                    "agent_id": "agent_0",
                    "claim": evidence["claim"],
                    "summary": evidence["summary"],
                    "source_url": "https://sequoiacap.com/investments",
                    "snippet": evidence["snippet"],
                    "confidence": 0.5,  # submitted value — should be overridden
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        # The insert call should have used computed confidence, not the submitted 0.5
        insert_call = state.db.fetchrow.call_args
        # confidence is the 7th positional arg (index 6) in the SQL params
        called_confidence = insert_call.args[7]  # $7 = confidence
        # Official domain should give >= 0.9
        assert called_confidence >= 0.9

    @pytest.mark.anyio
    async def test_ingest_with_screenshot_base64_triggers_background(self):
        """When screenshot_base64 is provided, a background upload task is queued."""
        evidence = _make_evidence()
        state = _mock_app_state(evidence=evidence)
        app.state = state

        fake_image = base64.b64encode(b"fakepng").decode()

        with patch("evidence.router._upload_screenshot_background"):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/evidence",
                    json={
                        "mission_id": evidence["mission_id"],
                        "agent_id": "agent_0",
                        "claim": "test",
                        "summary": "test",
                        "source_url": "https://example.com",
                        "snippet": "test",
                        "screenshot_base64": fake_image,
                    },
                )

            assert resp.status_code == 201

    @pytest.mark.anyio
    async def test_list_evidence_includes_screenshot_url(self):
        """When screenshot_s3_key is set, response should include screenshot_url."""
        evidence = _make_evidence(
            screenshot_s3_key="evidence/mid/eid.png",
        )
        state = _mock_app_state(evidence_list=[evidence])
        app.state = state

        with patch("evidence.screenshot.get_screenshot_url") as mock_url:
            mock_url.return_value = "https://minio/presigned-url"
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/missions/{evidence['mission_id']}/evidence")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["screenshot_url"] == "https://minio/presigned-url"

    @pytest.mark.anyio
    async def test_list_evidence_no_screenshot_url_when_no_key(self):
        """When screenshot_s3_key is None, screenshot_url should be None."""
        evidence = _make_evidence(screenshot_s3_key=None)
        state = _mock_app_state(evidence_list=[evidence])
        app.state = state

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/missions/{evidence['mission_id']}/evidence")

        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["screenshot_url"] is None

    @pytest.mark.anyio
    async def test_evidence_response_includes_embedding_id(self):
        """EvidenceResponse should include the embedding_id field."""
        evidence = _make_evidence(embedding_id="opensearch_doc_123")
        state = _mock_app_state(evidence_list=[evidence])
        app.state = state

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/missions/{evidence['mission_id']}/evidence")

        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["embedding_id"] == "opensearch_doc_123"


# ===========================================================================
# Repository — new update functions
# ===========================================================================


class TestRepositoryUpdates:
    """Test new asyncpg repository update functions."""

    @pytest.mark.anyio
    async def test_update_screenshot_key(self):
        from evidence.repository import update_screenshot_key

        pool = AsyncMock()
        pool.execute = AsyncMock()

        await update_screenshot_key(pool, "eid-123", "evidence/mid/eid.png")
        pool.execute.assert_called_once()
        args = pool.execute.call_args.args
        assert "screenshot_s3_key" in args[0]
        assert args[1] == "evidence/mid/eid.png"
        assert args[2] == "eid-123"

    @pytest.mark.anyio
    async def test_update_confidence(self):
        from evidence.repository import update_confidence

        pool = AsyncMock()
        pool.execute = AsyncMock()

        await update_confidence(pool, "eid-123", 0.95)
        pool.execute.assert_called_once()
        args = pool.execute.call_args.args
        assert "confidence" in args[0]
        assert args[1] == 0.95

    @pytest.mark.anyio
    async def test_update_novelty(self):
        from evidence.repository import update_novelty

        pool = AsyncMock()
        pool.execute = AsyncMock()

        await update_novelty(pool, "eid-123", 0.42)
        pool.execute.assert_called_once()
        args = pool.execute.call_args.args
        assert "novelty" in args[0]
        assert args[1] == 0.42

    @pytest.mark.anyio
    async def test_update_embedding_id(self):
        from evidence.repository import update_embedding_id

        pool = AsyncMock()
        pool.execute = AsyncMock()

        await update_embedding_id(pool, "eid-123", "os_doc_abc")
        pool.execute.assert_called_once()
        args = pool.execute.call_args.args
        assert "embedding_id" in args[0]
        assert args[1] == "os_doc_abc"

    @pytest.mark.anyio
    async def test_update_theme(self):
        from evidence.repository import update_theme

        pool = AsyncMock()
        pool.execute = AsyncMock()

        await update_theme(pool, "eid-123", "AI Investments")
        pool.execute.assert_called_once()

    @pytest.mark.anyio
    async def test_update_theme_batch(self):
        from evidence.repository import update_theme_batch

        pool = AsyncMock()
        pool.executemany = AsyncMock()

        ids = ["eid-1", "eid-2", "eid-3"]
        await update_theme_batch(pool, ids, "Founder Complaints")
        pool.executemany.assert_called_once()
        call_args = pool.executemany.call_args.args
        assert len(call_args[1]) == 3  # 3 tuples


# ===========================================================================
# Live Bedrock test (only runs with real credentials)
# ===========================================================================


@pytest.mark.live
@pytest.mark.anyio
async def test_embedding_client_live():
    """Test embedding client against live Bedrock API.

    Run with: pytest -m live -v
    Requires AWS_BEARER_TOKEN_BEDROCK in environment.
    """
    import os

    token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    if not token:
        pytest.skip("AWS_BEARER_TOKEN_BEDROCK not set")

    from models.embedding_client import EMBEDDING_DIMENSION, EmbeddingClient

    client = EmbeddingClient(bearer_token=token)
    try:
        # Text embedding
        vec = await client.embed("Sequoia Capital invests in AI startups")
        assert len(vec) == EMBEDDING_DIMENSION
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 0.001

        # Evidence convenience method
        vec2 = await client.embed_evidence(
            claim="Sequoia invested $100M",
            summary="Major AI investment",
            snippet="Detailed article text...",
        )
        assert len(vec2) == EMBEDDING_DIMENSION

        # Similarity sanity check
        vec_similar = await client.embed("Sequoia Capital AI investment fund")
        vec_different = await client.embed("Recipe for chocolate cake")
        sim_close = sum(a * b for a, b in zip(vec, vec_similar))
        sim_far = sum(a * b for a, b in zip(vec, vec_different))
        assert sim_close > sim_far
    finally:
        await client.close()
