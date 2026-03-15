"""Bedrock Titan Multimodal Embeddings client for Mission Control.

Uses the Bedrock Runtime REST API with bearer token auth to generate
1024-dimensional vectors from text and optional images.

Model: amazon.titan-embed-image-v1
Dimension: 1024
Auth: Bearer token (AWS_BEARER_TOKEN_BEDROCK), not IAM SigV4.
"""

from __future__ import annotations

import base64
import json
import logging
import math
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — share EMBEDDING_DIMENSION with Manav for OpenSearch index (Task 2.5)
# ---------------------------------------------------------------------------

EMBEDDING_MODEL_ID = "amazon.titan-embed-image-v1"
EMBEDDING_DIMENSION = 1024

_BEDROCK_RUNTIME_BASE = "https://bedrock-runtime.{region}.amazonaws.com"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _l2_normalize(vector: list[float]) -> list[float]:
    """L2-normalize a vector so cosine similarity works in OpenSearch."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        return vector
    return [x / norm for x in vector]


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

_retry_on_transient = retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class EmbeddingClient:
    """Async embedding client using Bedrock Titan Multimodal Embeddings.

    Usage::

        client = EmbeddingClient(bearer_token="ABSK...")
        vector = await client.embed("some evidence text")
        assert len(vector) == EMBEDDING_DIMENSION  # 1024
    """

    def __init__(
        self,
        bearer_token: str | None = None,
        region: str | None = None,
        model_id: str = EMBEDDING_MODEL_ID,
    ) -> None:
        if bearer_token is None:
            try:
                from config import settings  # type: ignore[import]

                bearer_token = settings.aws_bearer_token_bedrock or None
                region = region or settings.aws_region
            except Exception:
                pass

        if not bearer_token:
            import os

            bearer_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")

        if not bearer_token:
            raise ValueError(
                "Bedrock bearer token required. "
                "Set AWS_BEARER_TOKEN_BEDROCK env var or pass bearer_token=."
            )

        self._region = region or "us-east-1"
        self._model_id = model_id
        self._invoke_url = (
            f"{_BEDROCK_RUNTIME_BASE.format(region=self._region)}"
            f"/model/{self._model_id}/invoke"
        )
        self._headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(timeout=30.0)

    # ------------------------------------------------------------------
    # Core embedding method
    # ------------------------------------------------------------------

    @_retry_on_transient
    async def embed(
        self,
        text: str,
        image_bytes: bytes | None = None,
    ) -> list[float]:
        """Generate an embedding vector from text and optional image.

        Args:
            text: Text content to embed (required).
            image_bytes: Optional raw image bytes (PNG/JPEG) for multimodal.

        Returns:
            L2-normalized float vector of length EMBEDDING_DIMENSION (1024).

        Raises:
            httpx.HTTPStatusError: On non-retryable API errors.
            ValueError: If response shape is unexpected.
        """
        body: dict[str, Any] = {"inputText": text}
        if image_bytes is not None:
            body["inputImage"] = base64.b64encode(image_bytes).decode()

        response = await self._client.post(
            self._invoke_url,
            headers=self._headers,
            content=json.dumps(body),
        )
        response.raise_for_status()

        result = response.json()
        raw_vector = result["embedding"]

        if len(raw_vector) != EMBEDDING_DIMENSION:
            logger.warning(
                "Expected %d dimensions, got %d",
                EMBEDDING_DIMENSION,
                len(raw_vector),
            )

        return _l2_normalize(raw_vector)

    # ------------------------------------------------------------------
    # Convenience method for evidence
    # ------------------------------------------------------------------

    async def embed_evidence(
        self,
        claim: str,
        summary: str,
        snippet: str,
        image_bytes: bytes | None = None,
    ) -> list[float]:
        """Build a text representation of an evidence item and embed it.

        Concatenates claim + summary + snippet (truncated to 500 chars)
        into a single text input for the embedding model.
        """
        text = f"{claim}. {summary}. {snippet[:500]}"
        return await self.embed(text, image_bytes=image_bytes)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return EMBEDDING_DIMENSION


# ---------------------------------------------------------------------------
# Module-level singleton factory
# ---------------------------------------------------------------------------


def get_embedding_client(
    bearer_token: str | None = None,
) -> EmbeddingClient:
    """Return an EmbeddingClient, reading AWS_BEARER_TOKEN_BEDROCK from env."""
    return EmbeddingClient(bearer_token=bearer_token)


# ---------------------------------------------------------------------------
# Quick smoke test — run directly: python models/embedding_client.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    import os
    import sys

    async def _smoke_test() -> None:
        token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
        if not token:
            print("Set AWS_BEARER_TOKEN_BEDROCK to run the smoke test.")
            sys.exit(1)

        client = EmbeddingClient(bearer_token=token)
        print(f"Model: {client.model_id}")
        print(f"Expected dimension: {client.dimension}")
        print("─" * 50)

        # Test 1: text-only embedding
        print("Test 1 — text-only embedding:")
        vec = await client.embed("Sequoia Capital invests in AI startups")
        print(f"  Vector length: {len(vec)}")
        norm = math.sqrt(sum(x * x for x in vec))
        print(f"  L2 norm: {norm:.6f} (should be ≈ 1.0)")
        assert len(vec) == EMBEDDING_DIMENSION, f"Wrong dimension: {len(vec)}"
        assert abs(norm - 1.0) < 0.001, f"Not normalized: {norm}"
        print("  ✓ PASSED")

        # Test 2: evidence convenience method
        print("\nTest 2 — embed_evidence:")
        vec2 = await client.embed_evidence(
            claim="Sequoia invested $100M in AI startup",
            summary="Major AI investment by Sequoia Capital",
            snippet="According to sources, Sequoia Capital has invested $100M...",
        )
        print(f"  Vector length: {len(vec2)}")
        assert len(vec2) == EMBEDDING_DIMENSION
        print("  ✓ PASSED")

        # Test 3: cosine similarity sanity
        print("\nTest 3 — cosine similarity sanity:")
        vec_similar = await client.embed("Sequoia Capital AI investment fund")
        vec_different = await client.embed("Recipe for chocolate cake with sprinkles")
        sim_close = sum(a * b for a, b in zip(vec, vec_similar))
        sim_far = sum(a * b for a, b in zip(vec, vec_different))
        print(f"  Similar topic similarity: {sim_close:.4f}")
        print(f"  Different topic similarity: {sim_far:.4f}")
        assert sim_close > sim_far, "Similar topics should have higher similarity"
        print("  ✓ PASSED")

        await client.close()
        print("\n✅ All embedding smoke tests passed.")

    asyncio.run(_smoke_test())
