"""Vector store abstraction for evidence embeddings.

Provides a VectorStore protocol with two implementations:
  - InMemoryVectorStore: for local dev/testing (no OpenSearch needed)
  - OpenSearchVectorStore: for production (requires Manav's Task 2.5)

When Manav provisions OpenSearch, swap get_vector_store() to return
OpenSearchVectorStore. The pipeline code doesn't change.
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)

INDEX_NAME = "evidence_vectors"


@dataclass
class VectorDocument:
    """A document stored in the vector index."""

    doc_id: str
    mission_id: str
    evidence_id: str
    text_summary: str
    embedding: list[float]


@dataclass
class SearchHit:
    """A single search result from k-NN search."""

    doc_id: str
    evidence_id: str
    score: float  # cosine similarity (0.0 – 1.0)


class VectorStore(Protocol):
    """Protocol for vector stores (OpenSearch or in-memory)."""

    async def index(self, doc: VectorDocument) -> str:
        """Index a document. Returns the document ID."""
        ...

    async def search(
        self,
        vector: list[float],
        mission_id: str,
        k: int = 5,
        exclude_ids: list[str] | None = None,
    ) -> list[SearchHit]:
        """k-NN search within a mission's evidence. Returns top-k hits."""
        ...

    async def get_all_vectors(
        self,
        mission_id: str,
    ) -> list[VectorDocument]:
        """Fetch all vectors for a mission (for clustering)."""
        ...


# ---------------------------------------------------------------------------
# In-memory implementation (local dev / testing)
# ---------------------------------------------------------------------------


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryVectorStore:
    """In-memory vector store using brute-force cosine similarity.

    Suitable for development and testing. Stores vectors in a dict
    keyed by doc_id. Search is O(n) per query — fine for < 1000 docs.

    Thread-safe for single-process asyncio (no locks needed since
    we don't yield between read and write within a single operation).
    """

    def __init__(self) -> None:
        self._docs: dict[str, VectorDocument] = {}

    async def index(self, doc: VectorDocument) -> str:
        if not doc.doc_id:
            doc.doc_id = str(uuid.uuid4())
        self._docs[doc.doc_id] = doc
        logger.debug(
            "Indexed vector doc %s for evidence %s",
            doc.doc_id,
            doc.evidence_id,
        )
        return doc.doc_id

    async def search(
        self,
        vector: list[float],
        mission_id: str,
        k: int = 5,
        exclude_ids: list[str] | None = None,
    ) -> list[SearchHit]:
        exclude = set(exclude_ids or [])
        candidates = [
            d
            for d in self._docs.values()
            if d.mission_id == mission_id and d.doc_id not in exclude
        ]

        scored = [
            SearchHit(
                doc_id=d.doc_id,
                evidence_id=d.evidence_id,
                score=_cosine_similarity(vector, d.embedding),
            )
            for d in candidates
        ]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]

    async def get_all_vectors(self, mission_id: str) -> list[VectorDocument]:
        return [d for d in self._docs.values() if d.mission_id == mission_id]

    @property
    def count(self) -> int:
        return len(self._docs)

    def clear(self) -> None:
        self._docs.clear()


# ---------------------------------------------------------------------------
# OpenSearch implementation (production — requires Manav's Task 2.5)
# ---------------------------------------------------------------------------


class OpenSearchVectorStore:
    """OpenSearch Serverless vector store with k-NN.

    Requires opensearch-py[async] and AWS4Auth for SigV4 signing.
    Not yet active — waiting for Manav to provision the cluster (Task 2.5).
    """

    def __init__(self, endpoint: str, region: str = "us-east-1") -> None:
        self._endpoint = endpoint
        self._region = region
        # TODO: Initialize opensearch-py async client with AWS4Auth
        # from opensearchpy import AsyncOpenSearch, AWSV4SignerAuth
        raise NotImplementedError(
            "OpenSearchVectorStore requires Manav's Task 2.5 (OpenSearch provisioning). "
            "Use InMemoryVectorStore for local development."
        )

    async def index(self, doc: VectorDocument) -> str:
        raise NotImplementedError

    async def search(
        self,
        vector: list[float],
        mission_id: str,
        k: int = 5,
        exclude_ids: list[str] | None = None,
    ) -> list[SearchHit]:
        raise NotImplementedError

    async def get_all_vectors(self, mission_id: str) -> list[VectorDocument]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Factory — swap implementation here when OpenSearch is ready
# ---------------------------------------------------------------------------

_store: InMemoryVectorStore | None = None


def get_vector_store() -> InMemoryVectorStore:
    """Return the singleton vector store instance.

    Currently returns InMemoryVectorStore. When Manav provisions
    OpenSearch (Task 2.5), update this to return OpenSearchVectorStore.
    """
    global _store
    if _store is None:
        _store = InMemoryVectorStore()
    return _store
