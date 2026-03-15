"""Semantic clustering of evidence vectors — Task 7.3.

Fetches all evidence vectors for a mission from the vector store,
runs HDBSCAN clustering, and returns cluster assignments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from evidence.vector_store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class ClusterGroup:
    """A group of evidence items that belong to the same semantic cluster."""

    cluster_id: int
    evidence_ids: list[str]


async def cluster_evidence(
    mission_id: str,
    store: VectorStore | None = None,
) -> list[ClusterGroup]:
    """Fetch all vectors for a mission and cluster them with HDBSCAN.

    Args:
        mission_id: UUID of the mission.
        store: Vector store instance (defaults to singleton).

    Returns:
        List of ClusterGroup objects. Items with label -1 (noise)
        are each assigned to their own individual cluster so no
        evidence is lost.
    """
    if store is None:
        store = get_vector_store()

    docs = await store.get_all_vectors(mission_id)
    if len(docs) < 2:
        # Not enough items to cluster — return each as its own cluster
        return [
            ClusterGroup(cluster_id=i, evidence_ids=[d.evidence_id])
            for i, d in enumerate(docs)
        ]

    vectors = np.array([d.embedding for d in docs])
    evidence_ids = [d.evidence_id for d in docs]

    try:
        import hdbscan

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=2,
            metric="euclidean",
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(vectors)
    except ImportError:
        logger.warning("hdbscan not installed — falling back to simple cosine grouping")
        labels = _fallback_clustering(vectors)

    # Group evidence_ids by label
    groups: dict[int, list[str]] = {}
    noise_counter = 1000  # Assign individual cluster IDs to noise items
    for label, eid in zip(labels, evidence_ids):
        if label == -1:
            # Noise: assign each to its own cluster
            groups[noise_counter] = [eid]
            noise_counter += 1
        else:
            groups.setdefault(label, []).append(eid)

    result = [
        ClusterGroup(cluster_id=cid, evidence_ids=eids)
        for cid, eids in sorted(groups.items())
    ]

    logger.info(
        "Clustered %d evidence items into %d groups for mission %s",
        len(evidence_ids),
        len(result),
        mission_id,
    )
    return result


def _fallback_clustering(
    vectors: np.ndarray,
    threshold: float = 0.7,
) -> list[int]:
    """Simple greedy clustering fallback when hdbscan is not available.

    Groups vectors that have cosine similarity above the threshold.
    """
    n = len(vectors)
    labels = [-1] * n
    current_label = 0

    # Normalize for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normed = vectors / norms

    for i in range(n):
        if labels[i] != -1:
            continue
        labels[i] = current_label
        for j in range(i + 1, n):
            if labels[j] != -1:
                continue
            sim = float(np.dot(normed[i], normed[j]))
            if sim >= threshold:
                labels[j] = current_label
        current_label += 1

    return labels
