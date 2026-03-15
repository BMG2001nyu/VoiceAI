"""Embedding pipeline — Task 7.2.

Triggered as a background task after evidence ingest. Embeds the evidence
text (+ optional screenshot), indexes the vector, and computes novelty.
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg

from evidence import repository
from evidence.vector_store import VectorDocument, get_vector_store

logger = logging.getLogger(__name__)


async def run_embedding_pipeline(
    evidence: dict[str, Any],
    db: asyncpg.Pool,
) -> None:
    """Embed an evidence item, index it, and compute novelty.

    This runs as a non-blocking background task from POST /evidence.
    Evidence is still usable even if this pipeline fails.

    Steps:
        1. Build text from claim + summary + snippet (truncated).
        2. Call Bedrock Titan Embed for a 1024-dim vector.
        3. Index the vector in the vector store.
        4. Update embedding_id on the evidence record.
        5. Compute novelty via k-NN similarity search.
        6. Update novelty on the evidence record.
    """
    evidence_id = evidence["id"]
    mission_id = evidence["mission_id"]

    try:
        # Step 1: Build text for embedding
        text = (
            f"{evidence['claim']}. "
            f"{evidence['summary']}. "
            f"{evidence['snippet'][:500]}"
        )

        # Step 2: Get embedding from Bedrock
        from models.embedding_client import EmbeddingClient

        try:
            embed_client = EmbeddingClient()
        except ValueError:
            logger.warning(
                "Embedding client unavailable (no Bedrock token) "
                "for evidence %s — skipping embedding pipeline",
                evidence_id,
            )
            return

        image_bytes = None
        if evidence.get("screenshot_s3_key"):
            try:
                from evidence.screenshot import _get_s3_client

                s3, bucket = _get_s3_client()
                obj = s3.get_object(Bucket=bucket, Key=evidence["screenshot_s3_key"])
                image_bytes = obj["Body"].read()
            except Exception as exc:
                logger.warning(
                    "Could not fetch screenshot for multimodal embedding: %s",
                    exc,
                )

        vector = await embed_client.embed(text, image_bytes=image_bytes)

        # Step 3: Index in vector store
        store = get_vector_store()
        doc = VectorDocument(
            doc_id="",
            mission_id=str(mission_id),
            evidence_id=str(evidence_id),
            text_summary=text[:200],
            embedding=vector,
        )
        doc_id = await store.index(doc)

        # Step 4: Update embedding_id on evidence record
        await repository.update_embedding_id(db, str(evidence_id), doc_id)
        logger.info(
            "Embedded evidence %s → doc %s (%d dims)",
            evidence_id,
            doc_id,
            len(vector),
        )

        # Step 5-6: Compute and update novelty
        hits = await store.search(
            vector=vector,
            mission_id=str(mission_id),
            k=5,
            exclude_ids=[doc_id],
        )
        if hits:
            max_sim = max(h.score for h in hits)
            novelty = round(max(0.0, 1.0 - max_sim), 3)
        else:
            novelty = 1.0

        await repository.update_novelty(db, str(evidence_id), novelty)
        logger.info("Evidence %s novelty = %.3f", evidence_id, novelty)

        await embed_client.close()

    except Exception as exc:
        logger.error(
            "Embedding pipeline failed for evidence %s: %s",
            evidence_id,
            exc,
            exc_info=True,
        )
