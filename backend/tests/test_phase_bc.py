"""Comprehensive tests for Phase B+C: vector pipeline, clustering, themes, contradictions.

Tests for:
  - InMemoryVectorStore (index, search, get_all_vectors)
  - _cosine_similarity helper
  - Embedding pipeline (mock Bedrock + mock store)
  - Clustering (_fallback_clustering, cluster_evidence)
  - Theme labeler (mock LiteClient)
  - Contradiction detection (mock LiteClient + mock Redis)
  - Scoring helpers (compute_confidence, compute_novelty)
"""

import json
import uuid

import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from evidence.vector_store import (
    InMemoryVectorStore,
    VectorDocument,
    _cosine_similarity,
)
from evidence.clustering import ClusterGroup, _fallback_clustering, cluster_evidence
from evidence.scoring import compute_confidence, compute_novelty

# ---------------------------------------------------------------------------
# Helpers for building test data
# ---------------------------------------------------------------------------


def _make_doc(
    mission_id: str = "m1",
    evidence_id: str | None = None,
    embedding: list[float] | None = None,
    doc_id: str | None = None,
) -> VectorDocument:
    return VectorDocument(
        doc_id=doc_id or str(uuid.uuid4()),
        mission_id=mission_id,
        evidence_id=evidence_id or str(uuid.uuid4()),
        text_summary="Test summary",
        embedding=embedding or [1.0, 0.0, 0.0],
    )


# ===================================================================
# Vector Store Tests
# ===================================================================


class TestCosineSimHelper:
    """Tests for the module-level _cosine_similarity function."""

    def test_identical_vectors_return_one(self):
        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_zero(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors_return_negative_one(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_both_zero_vectors_return_zero(self):
        a = [0.0, 0.0]
        b = [0.0, 0.0]
        assert _cosine_similarity(a, b) == 0.0


class TestInMemoryVectorStore:
    """Tests for InMemoryVectorStore."""

    async def test_index_returns_doc_id(self):
        store = InMemoryVectorStore()
        doc = _make_doc(doc_id="doc-1")
        result = await store.index(doc)
        assert result == "doc-1"

    async def test_index_generates_uuid_if_empty(self):
        store = InMemoryVectorStore()
        doc = _make_doc(doc_id="")
        result = await store.index(doc)
        # Should be a valid UUID, not empty
        assert result != ""
        uuid.UUID(result)  # raises ValueError if invalid

    async def test_count_increments_on_index(self):
        store = InMemoryVectorStore()
        assert store.count == 0
        await store.index(_make_doc())
        assert store.count == 1
        await store.index(_make_doc())
        assert store.count == 2

    async def test_clear_resets_store(self):
        store = InMemoryVectorStore()
        await store.index(_make_doc())
        await store.index(_make_doc())
        assert store.count == 2
        store.clear()
        assert store.count == 0

    async def test_search_returns_top_k_by_cosine_similarity(self):
        store = InMemoryVectorStore()
        # Index three docs with known embeddings
        await store.index(_make_doc(evidence_id="close", embedding=[1.0, 0.1, 0.0]))
        await store.index(_make_doc(evidence_id="medium", embedding=[0.5, 0.5, 0.0]))
        await store.index(_make_doc(evidence_id="far", embedding=[0.0, 0.0, 1.0]))

        query = [1.0, 0.0, 0.0]
        hits = await store.search(query, mission_id="m1", k=2)
        assert len(hits) == 2
        # The closest match should be "close"
        assert hits[0].evidence_id == "close"
        assert hits[0].score > hits[1].score

    async def test_search_filters_by_mission_id(self):
        store = InMemoryVectorStore()
        await store.index(_make_doc(mission_id="m1", evidence_id="e1"))
        await store.index(_make_doc(mission_id="m2", evidence_id="e2"))

        hits = await store.search([1.0, 0.0, 0.0], mission_id="m1")
        assert len(hits) == 1
        assert hits[0].evidence_id == "e1"

    async def test_search_excludes_specified_doc_ids(self):
        store = InMemoryVectorStore()
        doc = _make_doc(doc_id="exclude-me", evidence_id="e1")
        await store.index(doc)
        await store.index(_make_doc(doc_id="keep-me", evidence_id="e2"))

        hits = await store.search(
            [1.0, 0.0, 0.0], mission_id="m1", exclude_ids=["exclude-me"]
        )
        assert len(hits) == 1
        assert hits[0].evidence_id == "e2"

    async def test_search_returns_empty_for_no_matches(self):
        store = InMemoryVectorStore()
        hits = await store.search([1.0, 0.0, 0.0], mission_id="m1")
        assert hits == []

    async def test_get_all_vectors_filters_by_mission_id(self):
        store = InMemoryVectorStore()
        await store.index(_make_doc(mission_id="m1", evidence_id="e1"))
        await store.index(_make_doc(mission_id="m1", evidence_id="e2"))
        await store.index(_make_doc(mission_id="m2", evidence_id="e3"))

        results = await store.get_all_vectors("m1")
        assert len(results) == 2
        eids = {d.evidence_id for d in results}
        assert eids == {"e1", "e2"}


# ===================================================================
# Clustering Tests
# ===================================================================


class TestFallbackClustering:
    """Tests for _fallback_clustering greedy cosine grouping."""

    def test_groups_similar_vectors_together(self):
        # Two similar vectors and one different
        vectors = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.99, 0.1, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        labels = _fallback_clustering(vectors, threshold=0.7)
        # First two should share a label, third should differ
        assert labels[0] == labels[1]
        assert labels[0] != labels[2]

    def test_different_vectors_get_different_labels(self):
        vectors = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        labels = _fallback_clustering(vectors, threshold=0.9)
        assert len(set(labels)) == 3

    def test_single_vector(self):
        vectors = np.array([[1.0, 0.0, 0.0]])
        labels = _fallback_clustering(vectors)
        assert labels == [0]

    def test_all_identical_vectors_same_cluster(self):
        vectors = np.array([[1.0, 0.5, 0.0]] * 5)
        labels = _fallback_clustering(vectors, threshold=0.7)
        assert len(set(labels)) == 1


class TestClusterEvidence:
    """Tests for the cluster_evidence async function."""

    async def test_fewer_than_two_docs_returns_individual_clusters(self):
        store = InMemoryVectorStore()
        await store.index(_make_doc(mission_id="m1", evidence_id="e1"))

        clusters = await cluster_evidence("m1", store=store)
        assert len(clusters) == 1
        assert clusters[0].evidence_ids == ["e1"]

    async def test_empty_store_returns_empty(self):
        store = InMemoryVectorStore()
        clusters = await cluster_evidence("m1", store=store)
        assert clusters == []

    async def test_with_fallback_clustering(self):
        """When hdbscan import fails, fallback clustering should run."""
        store = InMemoryVectorStore()
        # Two similar and one different
        await store.index(
            _make_doc(mission_id="m1", evidence_id="e1", embedding=[1.0, 0.0, 0.0])
        )
        await store.index(
            _make_doc(mission_id="m1", evidence_id="e2", embedding=[0.98, 0.1, 0.0])
        )
        await store.index(
            _make_doc(mission_id="m1", evidence_id="e3", embedding=[0.0, 0.0, 1.0])
        )

        # Force hdbscan import to fail so fallback is used
        with patch.dict("sys.modules", {"hdbscan": None}):
            clusters = await cluster_evidence("m1", store=store)

        # Should produce at least 2 clusters (e1+e2 together, e3 separate)
        assert len(clusters) >= 2
        all_eids = []
        for c in clusters:
            all_eids.extend(c.evidence_ids)
        assert set(all_eids) == {"e1", "e2", "e3"}

    async def test_noise_items_get_individual_clusters(self):
        """Items with label -1 from HDBSCAN should each get their own cluster."""
        store = InMemoryVectorStore()
        await store.index(
            _make_doc(mission_id="m1", evidence_id="e1", embedding=[1.0, 0.0, 0.0])
        )
        await store.index(
            _make_doc(mission_id="m1", evidence_id="e2", embedding=[0.0, 1.0, 0.0])
        )

        # Mock hdbscan to return all noise labels (-1)
        mock_hdbscan = MagicMock()
        mock_clusterer = MagicMock()
        mock_clusterer.fit_predict.return_value = np.array([-1, -1])
        mock_hdbscan.HDBSCAN.return_value = mock_clusterer

        with patch.dict("sys.modules", {"hdbscan": mock_hdbscan}):
            clusters = await cluster_evidence("m1", store=store)

        # Each noise item should be its own cluster
        assert len(clusters) == 2
        assert clusters[0].evidence_ids == ["e1"]
        assert clusters[1].evidence_ids == ["e2"]


# ===================================================================
# Theme Labeler Tests
# ===================================================================


class TestThemeLabeler:
    """Tests for label_cluster and label_all_clusters."""

    async def test_label_cluster_calls_lite_client_and_returns_label(self):
        cluster = ClusterGroup(cluster_id=0, evidence_ids=["e1", "e2"])

        # Mock DB to return evidence summaries
        mock_db = AsyncMock()
        mock_db.fetch.return_value = [
            {
                "claim": "AI investment growing",
                "summary": "Major VC firms invest in AI",
            },
        ]

        # Mock LiteClient to return a theme label
        mock_lite = AsyncMock()
        mock_lite.chat.return_value = "Venture Capital AI Trends"

        with patch("models.lite_client.LiteClient", return_value=mock_lite):
            from evidence.theme_labeler import label_cluster

            result = await label_cluster(cluster, mock_db)

        assert result == "Venture Capital AI Trends"
        mock_lite.chat.assert_called_once()

    async def test_label_cluster_with_empty_summaries_returns_uncategorized(self):
        cluster = ClusterGroup(cluster_id=0, evidence_ids=["e1"])

        mock_db = AsyncMock()
        mock_db.fetch.return_value = []  # No rows found

        from evidence.theme_labeler import label_cluster

        result = await label_cluster(cluster, mock_db)
        assert result == "Uncategorized"

    async def test_label_cluster_truncates_long_labels(self):
        cluster = ClusterGroup(cluster_id=0, evidence_ids=["e1"])

        mock_db = AsyncMock()
        mock_db.fetch.return_value = [
            {"claim": "Test claim", "summary": "Test summary"},
        ]

        mock_lite = AsyncMock()
        # Return a label longer than 60 chars
        mock_lite.chat.return_value = "A" * 100

        with patch("models.lite_client.LiteClient", return_value=mock_lite):
            from evidence.theme_labeler import label_cluster

            result = await label_cluster(cluster, mock_db)

        assert len(result) <= 60

    async def test_label_cluster_handles_llm_failure_gracefully(self):
        cluster = ClusterGroup(cluster_id=0, evidence_ids=["e1"])

        mock_db = AsyncMock()
        mock_db.fetch.return_value = [
            {"claim": "Test", "summary": "Summary"},
        ]

        with patch(
            "models.lite_client.LiteClient",
            side_effect=RuntimeError("Connection refused"),
        ):
            from evidence.theme_labeler import label_cluster

            result = await label_cluster(cluster, mock_db)

        assert result == "Research Findings"

    async def test_label_cluster_strips_quotes_and_punctuation(self):
        cluster = ClusterGroup(cluster_id=0, evidence_ids=["e1"])

        mock_db = AsyncMock()
        mock_db.fetch.return_value = [
            {"claim": "Claim", "summary": "Summary"},
        ]

        mock_lite = AsyncMock()
        mock_lite.chat.return_value = '  "Market Growth Analysis."  '

        with patch("models.lite_client.LiteClient", return_value=mock_lite):
            from evidence.theme_labeler import label_cluster

            result = await label_cluster(cluster, mock_db)

        # Quotes, periods, and whitespace should be stripped
        assert result == "Market Growth Analysis"

    async def test_label_all_clusters_labels_all_and_calls_batch_update(self):
        clusters = [
            ClusterGroup(cluster_id=0, evidence_ids=["e1", "e2"]),
            ClusterGroup(cluster_id=1, evidence_ids=["e3"]),
        ]

        mock_db = AsyncMock()
        mock_db.fetch.return_value = [
            {"claim": "Test", "summary": "Summary"},
        ]

        mock_lite = AsyncMock()
        mock_lite.chat.side_effect = ["AI Investments", "Market Trends"]

        with (
            patch("models.lite_client.LiteClient", return_value=mock_lite),
            patch("evidence.theme_labeler.repository") as mock_repo,
        ):
            mock_repo.update_theme_batch = AsyncMock()

            from evidence.theme_labeler import label_all_clusters

            result = await label_all_clusters(clusters, mock_db)

        assert result == {0: "AI Investments", 1: "Market Trends"}
        assert mock_repo.update_theme_batch.call_count == 2


# ===================================================================
# Contradiction Detection Tests
# ===================================================================


class TestContradictionDetection:
    """Tests for detect_contradictions and _llm_batch_detect."""

    async def test_detect_contradictions_with_cached_result_returns_cache(self):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        cached_data = json.dumps(
            [
                {
                    "evidence_id_a": "a1",
                    "evidence_id_b": "b1",
                    "description": "They disagree",
                }
            ]
        )
        mock_redis.get.return_value = cached_data

        from evidence.contradictions import detect_contradictions

        result = await detect_contradictions("m1", mock_db, redis=mock_redis)

        assert len(result) == 1
        assert result[0].evidence_id_a == "a1"
        assert result[0].evidence_id_b == "b1"
        assert result[0].description == "They disagree"
        # DB should not have been queried since cache was hit
        mock_db.fetch.assert_not_called()

    async def test_detect_contradictions_with_fewer_than_two_rows_returns_empty(self):
        mock_db = AsyncMock()
        mock_db.fetch.return_value = [
            {"id": "e1", "claim": "Only one claim", "summary": "Summary"},
        ]
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # cache miss

        from evidence.contradictions import detect_contradictions

        result = await detect_contradictions("m1", mock_db, redis=mock_redis)
        assert result == []

    async def test_detect_contradictions_no_rows_returns_empty(self):
        mock_db = AsyncMock()
        mock_db.fetch.return_value = []
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        from evidence.contradictions import detect_contradictions

        result = await detect_contradictions("m1", mock_db, redis=mock_redis)
        assert result == []

    async def test_detect_contradictions_caches_result_in_redis(self):
        mock_db = AsyncMock()
        mock_db.fetch.return_value = [
            {"id": "e1", "claim": "Claim A", "summary": "Summary A"},
            {"id": "e2", "claim": "Claim B", "summary": "Summary B"},
        ]
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # cache miss

        mock_lite = AsyncMock()
        # LLM returns no contradictions
        mock_lite.chat.return_value = "[]"

        with patch("models.lite_client.LiteClient", return_value=mock_lite):
            from evidence.contradictions import detect_contradictions

            await detect_contradictions("m1", mock_db, redis=mock_redis)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "mission:m1:contradictions"
        assert call_args[0][1] == 30  # TTL

    async def test_llm_batch_detect_parses_valid_json(self):
        rows = [
            {"id": "e1", "claim": "Revenue is $10M", "summary": "S1"},
            {"id": "e2", "claim": "Revenue is $50M", "summary": "S2"},
        ]

        response_json = json.dumps(
            [
                {"a_id": "e1", "b_id": "e2", "reason": "Revenue figures conflict"},
            ]
        )

        mock_lite = AsyncMock()
        mock_lite.chat.return_value = response_json

        with patch("models.lite_client.LiteClient", return_value=mock_lite):
            from evidence.contradictions import _llm_batch_detect

            result = await _llm_batch_detect(rows)

        assert len(result) == 1
        assert result[0].evidence_id_a == "e1"
        assert result[0].evidence_id_b == "e2"
        assert result[0].description == "Revenue figures conflict"

    async def test_llm_batch_detect_handles_invalid_json_gracefully(self):
        rows = [
            {"id": "e1", "claim": "Claim A", "summary": "S1"},
            {"id": "e2", "claim": "Claim B", "summary": "S2"},
        ]

        mock_lite = AsyncMock()
        mock_lite.chat.return_value = "This is not valid JSON at all!"

        with patch("models.lite_client.LiteClient", return_value=mock_lite):
            from evidence.contradictions import _llm_batch_detect

            result = await _llm_batch_detect(rows)

        # Should return empty list on parse failure, not raise
        assert result == []

    async def test_llm_batch_detect_validates_ids_exist(self):
        rows = [
            {"id": "e1", "claim": "Claim A", "summary": "S1"},
            {"id": "e2", "claim": "Claim B", "summary": "S2"},
        ]

        # LLM returns a pair where one ID does not exist in rows
        response_json = json.dumps(
            [
                {"a_id": "e1", "b_id": "e999", "reason": "Fake pair"},
                {"a_id": "e1", "b_id": "e2", "reason": "Real pair"},
            ]
        )

        mock_lite = AsyncMock()
        mock_lite.chat.return_value = response_json

        with patch("models.lite_client.LiteClient", return_value=mock_lite):
            from evidence.contradictions import _llm_batch_detect

            result = await _llm_batch_detect(rows)

        # Only the valid pair should be returned
        assert len(result) == 1
        assert result[0].evidence_id_a == "e1"
        assert result[0].evidence_id_b == "e2"

    async def test_llm_batch_detect_rejects_self_contradictions(self):
        rows = [
            {"id": "e1", "claim": "Claim", "summary": "S"},
            {"id": "e2", "claim": "Claim 2", "summary": "S2"},
        ]

        response_json = json.dumps(
            [
                {"a_id": "e1", "b_id": "e1", "reason": "Same item"},
            ]
        )

        mock_lite = AsyncMock()
        mock_lite.chat.return_value = response_json

        with patch("models.lite_client.LiteClient", return_value=mock_lite):
            from evidence.contradictions import _llm_batch_detect

            result = await _llm_batch_detect(rows)

        assert result == []

    async def test_llm_batch_detect_handles_markdown_code_fence(self):
        """LLM sometimes wraps JSON in ```json ... ``` fences."""
        rows = [
            {"id": "e1", "claim": "Up", "summary": "S1"},
            {"id": "e2", "claim": "Down", "summary": "S2"},
        ]

        response = '```json\n[{"a_id": "e1", "b_id": "e2", "reason": "Opposite"}]\n```'

        mock_lite = AsyncMock()
        mock_lite.chat.return_value = response

        with patch("models.lite_client.LiteClient", return_value=mock_lite):
            from evidence.contradictions import _llm_batch_detect

            result = await _llm_batch_detect(rows)

        assert len(result) == 1

    async def test_detect_contradictions_without_redis(self):
        """Should work when redis=None (no caching)."""
        mock_db = AsyncMock()
        mock_db.fetch.return_value = [
            {"id": "e1", "claim": "A", "summary": "S1"},
            {"id": "e2", "claim": "B", "summary": "S2"},
        ]

        mock_lite = AsyncMock()
        mock_lite.chat.return_value = "[]"

        with patch("models.lite_client.LiteClient", return_value=mock_lite):
            from evidence.contradictions import detect_contradictions

            result = await detect_contradictions("m1", mock_db, redis=None)

        assert result == []


# ===================================================================
# Embedding Pipeline Tests
# ===================================================================


class TestEmbeddingPipeline:
    """Tests for run_embedding_pipeline."""

    async def test_success_path(self):
        """Full happy path: embed, index, update embedding_id, compute novelty."""
        evidence = {
            "id": "ev-1",
            "mission_id": "m-1",
            "claim": "Test claim",
            "summary": "Test summary",
            "snippet": "Test snippet text",
            "screenshot_s3_key": None,
        }
        mock_db = AsyncMock()
        fake_vector = [0.1] * 1024

        mock_embed_client = AsyncMock()
        mock_embed_client.embed.return_value = fake_vector
        mock_embed_client.close = AsyncMock()

        mock_store = InMemoryVectorStore()

        with (
            patch(
                "models.embedding_client.EmbeddingClient",
                return_value=mock_embed_client,
            ),
            patch(
                "evidence.embedding_pipeline.get_vector_store",
                return_value=mock_store,
            ),
            patch("evidence.embedding_pipeline.repository") as mock_repo,
        ):
            mock_repo.update_embedding_id = AsyncMock()
            mock_repo.update_novelty = AsyncMock()

            from evidence.embedding_pipeline import run_embedding_pipeline

            await run_embedding_pipeline(evidence, mock_db)

        # Verify embedding was requested
        mock_embed_client.embed.assert_called_once()
        # Verify vector was indexed
        assert mock_store.count == 1
        # Verify DB was updated with embedding_id
        mock_repo.update_embedding_id.assert_called_once()
        # Verify novelty was computed and stored (first item = 1.0 novelty)
        mock_repo.update_novelty.assert_called_once_with(mock_db, "ev-1", 1.0)
        # Verify client was closed
        mock_embed_client.close.assert_called_once()

    async def test_handles_missing_bedrock_token_gracefully(self):
        """Pipeline should log and return (not crash) when no Bedrock token."""
        evidence = {
            "id": "ev-1",
            "mission_id": "m-1",
            "claim": "Claim",
            "summary": "Summary",
            "snippet": "Snippet",
        }
        mock_db = AsyncMock()

        with patch(
            "models.embedding_client.EmbeddingClient",
            side_effect=ValueError("Bedrock bearer token required"),
        ):
            from evidence.embedding_pipeline import run_embedding_pipeline

            # Should not raise
            await run_embedding_pipeline(evidence, mock_db)

    async def test_with_screenshot_fetches_from_s3(self):
        """When screenshot_s3_key is set, pipeline should fetch image from S3."""
        evidence = {
            "id": "ev-2",
            "mission_id": "m-1",
            "claim": "Claim",
            "summary": "Summary",
            "snippet": "Snippet",
            "screenshot_s3_key": "screenshots/ev-2.png",
        }
        mock_db = AsyncMock()
        fake_vector = [0.5] * 1024

        mock_embed_client = AsyncMock()
        mock_embed_client.embed.return_value = fake_vector
        mock_embed_client.close = AsyncMock()

        mock_s3 = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = b"fake-png-bytes"
        mock_s3.get_object.return_value = {"Body": mock_body}

        with (
            patch(
                "models.embedding_client.EmbeddingClient",
                return_value=mock_embed_client,
            ),
            patch(
                "evidence.embedding_pipeline.get_vector_store",
                return_value=InMemoryVectorStore(),
            ),
            patch("evidence.embedding_pipeline.repository") as mock_repo,
            patch(
                "evidence.screenshot._get_s3_client",
                return_value=(mock_s3, "evidence"),
            ),
        ):
            mock_repo.update_embedding_id = AsyncMock()
            mock_repo.update_novelty = AsyncMock()

            from evidence.embedding_pipeline import run_embedding_pipeline

            await run_embedding_pipeline(evidence, mock_db)

        # Verify embed was called with image_bytes
        call_kwargs = mock_embed_client.embed.call_args
        assert call_kwargs[1]["image_bytes"] == b"fake-png-bytes"

    async def test_computes_novelty_from_knn(self):
        """Novelty should be 1 - max_similarity when neighbors exist."""
        evidence = {
            "id": "ev-3",
            "mission_id": "m-1",
            "claim": "Claim",
            "summary": "Summary",
            "snippet": "Snippet",
            "screenshot_s3_key": None,
        }
        mock_db = AsyncMock()

        # Create a vector very similar to an existing one
        existing_vec = [1.0] + [0.0] * 1023
        new_vec = [0.99] + [0.1] + [0.0] * 1022

        mock_embed_client = AsyncMock()
        mock_embed_client.embed.return_value = new_vec
        mock_embed_client.close = AsyncMock()

        # Pre-populate the store with an existing vector
        store = InMemoryVectorStore()
        await store.index(
            VectorDocument(
                doc_id="existing-doc",
                mission_id="m-1",
                evidence_id="ev-existing",
                text_summary="Existing",
                embedding=existing_vec,
            )
        )

        with (
            patch(
                "models.embedding_client.EmbeddingClient",
                return_value=mock_embed_client,
            ),
            patch(
                "evidence.embedding_pipeline.get_vector_store",
                return_value=store,
            ),
            patch("evidence.embedding_pipeline.repository") as mock_repo,
        ):
            mock_repo.update_embedding_id = AsyncMock()
            mock_repo.update_novelty = AsyncMock()

            from evidence.embedding_pipeline import run_embedding_pipeline

            await run_embedding_pipeline(evidence, mock_db)

        # Novelty should be < 1.0 since a similar doc exists
        novelty_call = mock_repo.update_novelty.call_args
        novelty_value = novelty_call[0][2]
        assert 0.0 < novelty_value < 1.0

    async def test_pipeline_catches_unexpected_exceptions(self):
        """Pipeline should catch and log exceptions, not crash the caller."""
        evidence = {
            "id": "ev-err",
            "mission_id": "m-1",
            "claim": "Claim",
            "summary": "Summary",
            "snippet": "Snippet",
            "screenshot_s3_key": None,
        }
        mock_db = AsyncMock()

        mock_embed_client = AsyncMock()
        mock_embed_client.embed.side_effect = RuntimeError("Network error")

        with patch(
            "models.embedding_client.EmbeddingClient",
            return_value=mock_embed_client,
        ):
            from evidence.embedding_pipeline import run_embedding_pipeline

            # Should not raise
            await run_embedding_pipeline(evidence, mock_db)


# ===================================================================
# Scoring Tests
# ===================================================================


class TestComputeConfidence:
    """Tests for the compute_confidence heuristic."""

    def test_official_domain_gets_high_base(self):
        score = compute_confidence("https://www.sequoiacap.com/article/test", "x" * 100)
        assert score >= 0.9

    def test_unknown_domain_gets_lower_base(self):
        score = compute_confidence("https://random-blog.com/post", "x" * 100)
        assert 0.7 <= score < 0.9

    def test_longer_snippet_adds_bonus(self):
        short = compute_confidence("https://example.com", "short")
        long = compute_confidence("https://example.com", "x" * 3000)
        assert long > short

    def test_score_capped_at_one(self):
        score = compute_confidence("https://crunchbase.com/org/test", "x" * 10000)
        assert score <= 1.0

    def test_invalid_url_still_returns_score(self):
        score = compute_confidence("not a url", "some snippet")
        assert 0.0 < score <= 1.0

    def test_empty_snippet(self):
        score = compute_confidence("https://example.com", "")
        assert score == 0.7  # base only, no length bonus


class TestComputeNovelty:
    """Tests for the compute_novelty function."""

    async def test_returns_one_when_no_opensearch_client(self):
        result = await compute_novelty("e1", "m1", opensearch_client=None)
        assert result == 1.0

    async def test_returns_one_when_no_vector(self):
        mock_client = AsyncMock()
        result = await compute_novelty(
            "e1", "m1", opensearch_client=mock_client, vector=None
        )
        assert result == 1.0

    async def test_returns_one_when_no_hits(self):
        mock_client = AsyncMock()
        mock_client.search.return_value = {"hits": {"hits": []}}
        result = await compute_novelty(
            "e1", "m1", opensearch_client=mock_client, vector=[0.1] * 1024
        )
        assert result == 1.0

    async def test_computes_novelty_from_max_similarity(self):
        mock_client = AsyncMock()
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {"_id": "other-1", "_score": 0.8},
                    {"_id": "other-2", "_score": 0.3},
                ]
            }
        }
        result = await compute_novelty(
            "e1", "m1", opensearch_client=mock_client, vector=[0.1] * 1024
        )
        # novelty = 1 - max_sim = 1 - 0.8 = 0.2
        assert result == pytest.approx(0.2, abs=0.001)

    async def test_excludes_self_from_similarity(self):
        mock_client = AsyncMock()
        # Only hit is the item itself
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {"_id": "e1", "_score": 1.0},
                ]
            }
        }
        result = await compute_novelty(
            "e1", "m1", opensearch_client=mock_client, vector=[0.1] * 1024
        )
        # After excluding self, no other scores remain
        assert result == 1.0

    async def test_handles_search_exception_gracefully(self):
        mock_client = AsyncMock()
        mock_client.search.side_effect = RuntimeError("Connection lost")
        result = await compute_novelty(
            "e1", "m1", opensearch_client=mock_client, vector=[0.1] * 1024
        )
        assert result == 1.0
