"""Theme classification via Nova Lite — Task 7.4.

For each cluster of evidence, calls Nova Lite to assign a concise
theme label (3-6 words). Updates evidence records with the label.
"""

from __future__ import annotations

import logging

import asyncpg

from evidence import repository
from evidence.clustering import ClusterGroup

logger = logging.getLogger(__name__)


async def label_cluster(
    cluster: ClusterGroup,
    db: asyncpg.Pool,
) -> str:
    """Generate a theme label for a cluster of evidence items.

    Fetches evidence summaries from the DB, sends them to Nova Lite,
    and returns a short theme phrase (3-6 words).

    Args:
        cluster: A ClusterGroup with evidence_ids.
        db: asyncpg connection pool.

    Returns:
        A short theme label string.
    """
    # Fetch evidence summaries for this cluster
    summaries = []
    for eid in cluster.evidence_ids[:5]:  # Limit to 5 to avoid token overflow
        rows = await db.fetch(
            "SELECT claim, summary FROM evidence WHERE id = $1",
            eid,
        )
        if rows:
            row = rows[0]
            summaries.append(f"- {row['claim']}: {row['summary']}")

    if not summaries:
        return "Uncategorized"

    findings_text = "\n".join(summaries)

    prompt = (
        "Label this cluster of research findings with a short phrase "
        "(3-6 words). Just return the label, nothing else.\n\n"
        f"Findings:\n{findings_text}"
    )

    try:
        from models.lite_client import LiteClient

        client = LiteClient()
        label = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            system=(
                "You are a research analyst labeling clusters of evidence. "
                "Return ONLY a short theme label (3-6 words). "
                "No quotes, no punctuation, no explanation."
            ),
            temperature=0.1,
            max_tokens=30,
        )
        label = label.strip().strip('"').strip("'").strip(".")
        if len(label) > 60:
            label = label[:60]
        return label
    except Exception as exc:
        logger.warning("Theme labeling failed: %s — using fallback", exc)
        return "Research Findings"


async def label_all_clusters(
    clusters: list[ClusterGroup],
    db: asyncpg.Pool,
) -> dict[int, str]:
    """Label all clusters and batch-update evidence themes in the DB.

    Args:
        clusters: List of ClusterGroup objects from clustering.
        db: asyncpg connection pool.

    Returns:
        Dict mapping cluster_id to theme label.
    """
    labels: dict[int, str] = {}

    for cluster in clusters:
        theme = await label_cluster(cluster, db)
        labels[cluster.cluster_id] = theme

        # Batch update all evidence in this cluster with the theme
        await repository.update_theme_batch(db, cluster.evidence_ids, theme)
        logger.info(
            "Cluster %d → '%s' (%d items)",
            cluster.cluster_id,
            theme,
            len(cluster.evidence_ids),
        )

    return labels
