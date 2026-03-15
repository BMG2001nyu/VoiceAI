"""Pre-synthesis clustering and labelling — Task 12.1.

Runs the full clustering + labelling pipeline as the first step
when a mission transitions to SYNTHESIZING.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import asyncpg

from evidence.clustering import cluster_evidence
from evidence.theme_labeler import label_all_clusters

logger = logging.getLogger(__name__)


@dataclass
class ClusterSummary:
    """Summary of a cluster for the synthesis prompt."""

    theme: str
    evidence_count: int
    top_claims: list[str]


async def prepare_evidence_clusters(
    mission_id: str,
    db: asyncpg.Pool,
) -> list[ClusterSummary]:
    """Run clustering + labelling pipeline for synthesis.

    Steps:
        1. Cluster evidence vectors (HDBSCAN or fallback).
        2. Label each cluster with Nova Lite.
        3. Batch-update evidence.theme in DB.
        4. Fetch top claims per cluster for the synthesis prompt.

    Returns:
        List of ClusterSummary objects ready for briefing generation.
    """
    # Step 1: Cluster
    clusters = await cluster_evidence(mission_id)

    if not clusters:
        return []

    # Step 2-3: Label all clusters + batch update DB
    labels = await label_all_clusters(clusters, db)

    # Step 4: Build summaries with top claims
    summaries = []
    for cluster in clusters:
        theme = labels.get(cluster.cluster_id, "Uncategorized")

        # Fetch top claims from DB for this cluster
        top_claims = []
        for eid in cluster.evidence_ids[:3]:  # Top 3 claims
            rows = await db.fetch(
                "SELECT claim FROM evidence WHERE id = $1",
                eid,
            )
            if rows:
                top_claims.append(rows[0]["claim"])

        summaries.append(
            ClusterSummary(
                theme=theme,
                evidence_count=len(cluster.evidence_ids),
                top_claims=top_claims,
            )
        )

    logger.info(
        "Prepared %d cluster summaries for mission %s",
        len(summaries),
        mission_id,
    )
    return summaries
