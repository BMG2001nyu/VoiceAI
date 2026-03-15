"""Structured evidence emission — bridge between browser agents and the Evidence Service.

After a browser task completes, parses the BrowserResult into individual claims
and POSTs each to the evidence API. Uses Nova Lite for claim extraction.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)

# Maximum claims to extract per browser result
MAX_CLAIMS = 5
MIN_CLAIMS = 1


async def emit_findings(
    result: Any,  # BrowserResult from browser_session.py
    mission_id: UUID | str,
    agent_id: str,
    task_id: UUID | str,
    backend_url: str = "http://localhost:8000",
) -> int:
    """Parse browser result into claims and POST each to the evidence API.

    Args:
        result: BrowserResult from run_browser_task().
        mission_id: UUID of the active mission.
        agent_id: Agent ID (e.g., "agent_0").
        task_id: UUID of the task being worked.
        backend_url: Base URL of the backend API.

    Returns:
        Number of evidence records successfully posted.
    """
    if not result.success or not result.extracted_text:
        logger.warning("Agent %s: no findings to emit (success=%s)", agent_id, result.success)
        return 0

    # Extract individual claims using Nova Lite
    claims = await extract_claims(result.extracted_text, mission_id, agent_id)

    if not claims:
        # Fallback: create a single claim from the raw text
        claims = [
            {
                "claim": result.extracted_text[:200],
                "summary": result.extracted_text[:500],
                "snippet": result.extracted_text[:300],
            }
        ]

    posted = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, claim in enumerate(claims[:MAX_CLAIMS]):
            payload = {
                "mission_id": str(mission_id),
                "agent_id": agent_id,
                "claim": claim.get("claim", ""),
                "summary": claim.get("summary", ""),
                "source_url": str(result.source_url or ""),
                "snippet": claim.get("snippet", ""),
                "confidence": claim.get("confidence", 0.8),
                "theme": claim.get("theme"),
                # Only attach screenshot to first claim (cost saving)
                "screenshot_s3_key": None,
            }

            try:
                resp = await client.post(f"{backend_url}/evidence", json=payload)
                if resp.status_code in (200, 201):
                    posted += 1
                    logger.info(
                        "Agent %s: posted evidence %d/%d for task %s",
                        agent_id, i + 1, len(claims), task_id,
                    )
                else:
                    logger.warning(
                        "Agent %s: evidence POST returned %d: %s",
                        agent_id, resp.status_code, resp.text[:200],
                    )
            except httpx.HTTPError as exc:
                logger.error("Agent %s: evidence POST failed: %s", agent_id, exc)

    logger.info(
        "Agent %s: emitted %d/%d findings for task %s",
        agent_id, posted, len(claims), task_id,
    )
    return posted


async def extract_claims(
    text: str,
    mission_id: UUID | str,
    agent_id: str,
) -> list[dict[str, Any]]:
    """Use Nova Lite to extract structured claims from raw browser text.

    Args:
        text: Raw extracted text from browser session.
        mission_id: Mission UUID (for context).
        agent_id: Agent ID (for logging).

    Returns:
        List of claim dicts with keys: claim, summary, snippet, confidence, theme.
    """
    try:
        from models.lite_client import LiteClient
        from config import settings

        if not settings.nova_api_key:
            return _fallback_extract(text)

        client = LiteClient(api_key=settings.nova_api_key)
        prompt = (
            "Extract 2-5 distinct factual claims from this research text. "
            "Return a JSON array only (no markdown fences, no commentary).\n\n"
            "Each item must have these keys:\n"
            '  - "claim": one-sentence factual claim (max 200 chars)\n'
            '  - "summary": 2-3 sentence supporting context (max 500 chars)\n'
            '  - "snippet": verbatim quote from the text (max 300 chars)\n'
            '  - "confidence": float 0.0-1.0 (how well-supported is this claim)\n'
            '  - "theme": one of "investment", "strategy", "sentiment", "technical", '
            '"financial", "leadership", "product", "other"\n\n'
            f"TEXT:\n{text[:8000]}"
        )

        import json
        response = await client.chat(prompt)

        # Try to parse JSON from response
        response = response.strip()
        # Handle potential markdown fences
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1]) if len(lines) > 2 else response

        claims = json.loads(response)

        if not isinstance(claims, list):
            logger.warning("Agent %s: claims response is not a list", agent_id)
            return _fallback_extract(text)

        # Validate each claim
        validated = []
        for c in claims[:MAX_CLAIMS]:
            if isinstance(c, dict) and "claim" in c:
                validated.append({
                    "claim": str(c.get("claim", ""))[:200],
                    "summary": str(c.get("summary", ""))[:500],
                    "snippet": str(c.get("snippet", ""))[:300],
                    "confidence": min(1.0, max(0.0, float(c.get("confidence", 0.8)))),
                    "theme": c.get("theme"),
                })

        return validated if validated else _fallback_extract(text)

    except Exception as exc:
        logger.warning("Agent %s: claim extraction failed: %s", agent_id, exc)
        return _fallback_extract(text)


def _fallback_extract(text: str) -> list[dict[str, Any]]:
    """Simple fallback: split text into paragraph-based claims."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 50]
    claims = []
    for p in paragraphs[:3]:
        claims.append({
            "claim": p[:200],
            "summary": p[:500],
            "snippet": p[:300],
            "confidence": 0.6,
            "theme": "other",
        })
    return claims if claims else [{"claim": text[:200], "summary": text[:500], "snippet": text[:300], "confidence": 0.5, "theme": "other"}]
