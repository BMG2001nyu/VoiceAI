"""Confidence and novelty scoring for evidence items.

Confidence: heuristic based on source domain authority and snippet length.
Novelty: cosine-similarity-based deduplication via OpenSearch k-NN.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Domains considered authoritative for higher base confidence.
OFFICIAL_DOMAINS = frozenset(
    {
        "sequoiacap.com",
        "crunchbase.com",
        "pitchbook.com",
        "techcrunch.com",
        "bloomberg.com",
        "sec.gov",
        "linkedin.com",
        "github.com",
        "wsj.com",
        "reuters.com",
        "ft.com",
    }
)


def compute_confidence(source_url: str, snippet: str) -> float:
    """Compute confidence score from source domain and snippet length.

    Official/authoritative domains get a base score of 0.9; other domains
    get 0.7. Longer snippets add up to 0.1 bonus, capped at 1.0.

    Args:
        source_url: The URL where the evidence was found.
        snippet: The raw text snippet extracted by the browser agent.

    Returns:
        A confidence score between 0.0 and 1.0 (rounded to 3 decimals).
    """
    try:
        domain = urlparse(source_url).netloc.replace("www.", "")
    except Exception:
        domain = ""

    base = 0.9 if domain in OFFICIAL_DOMAINS else 0.7
    length_bonus = min(0.1, len(snippet) / 5000)
    return round(min(1.0, base + length_bonus), 3)


async def compute_novelty(
    evidence_id: str,
    mission_id: str,
    opensearch_client=None,
    vector: list[float] | None = None,
) -> float:
    """Compute novelty score based on cosine similarity to existing evidence.

    Returns 1.0 (fully novel) when no similar evidence exists or when
    OpenSearch is not available. Returns closer to 0.0 for near-duplicates.

    Args:
        evidence_id: UUID of the current evidence item (excluded from results).
        mission_id: UUID of the mission to scope the search.
        opensearch_client: An async OpenSearch client (None = stub mode).
        vector: The embedding vector for this evidence item.

    Returns:
        A novelty score between 0.0 and 1.0 (rounded to 3 decimals).
    """
    # Stub: return full novelty until Phase 7.2 embedding pipeline is live
    if opensearch_client is None or vector is None:
        return 1.0

    try:
        results = await opensearch_client.search(
            index="evidence_vectors",
            body={
                "size": 5,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": vector,
                            "k": 5,
                        }
                    }
                },
                "_source": False,
            },
        )
        hits = results.get("hits", {}).get("hits", [])
        if not hits:
            return 1.0

        other_scores = [h["_score"] for h in hits if h["_id"] != str(evidence_id)]
        if not other_scores:
            return 1.0

        max_sim = max(other_scores)
        return round(max(0.0, 1.0 - max_sim), 3)
    except Exception as exc:
        logger.warning("Novelty computation failed: %s", exc)
        return 1.0
