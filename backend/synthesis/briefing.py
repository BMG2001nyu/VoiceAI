"""Intelligence briefing generation — Task 12.2.

Calls Nova Lite with mission objective + themed evidence summaries
to generate a structured intelligence briefing.
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg

from synthesis.pre_synthesis import ClusterSummary

logger = logging.getLogger(__name__)


async def generate_briefing(
    mission_id: str,
    objective: str,
    cluster_summaries: list[ClusterSummary],
    contradictions: list[dict[str, Any]],
    db: asyncpg.Pool,
    redis: Any = None,
) -> str:
    """Generate the final intelligence briefing.

    Args:
        mission_id: UUID of the mission.
        objective: The mission's research objective.
        cluster_summaries: Pre-processed cluster data from pre_synthesis.
        contradictions: List of contradiction dicts.
        db: asyncpg pool for storing the result.
        redis: Redis client for publishing events (optional).

    Returns:
        The briefing text.
    """
    # Build evidence section
    evidence_sections = []
    for cs in cluster_summaries:
        claims_text = "\n".join(f"  - {c}" for c in cs.top_claims)
        evidence_sections.append(
            f"## {cs.theme} ({cs.evidence_count} findings)\n{claims_text}"
        )
    evidence_text = (
        "\n\n".join(evidence_sections) if evidence_sections else "No evidence gathered."
    )

    # Build contradictions section
    if contradictions:
        contra_lines = [
            f"  - {c.get('description', 'Contradiction detected')}"
            for c in contradictions
        ]
        contra_text = "\n".join(contra_lines)
    else:
        contra_text = "None detected."

    prompt = (
        f"Mission Objective: {objective}\n\n"
        f"Evidence by Theme:\n{evidence_text}\n\n"
        f"Contradictions:\n{contra_text}\n\n"
        "Produce a structured intelligence briefing with:\n"
        "1. Executive Summary (2-3 sentences)\n"
        "2. Key Findings by Theme (bullet points)\n"
        "3. Contradictions to Note\n"
        "4. Strategic Recommendations (2-3 bullets)\n\n"
        "Keep it tight — this will be spoken aloud. "
        "Avoid bullet nesting. Under 300 words."
    )

    try:
        from models.lite_client import LiteClient

        client = LiteClient()
        briefing_text = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            system=(
                "You are a senior intelligence analyst producing a structured "
                "briefing for an executive. Be concise, factual, and actionable. "
                "Use simple language suitable for spoken delivery."
            ),
            temperature=0.3,
            max_tokens=1024,
        )
    except Exception as exc:
        logger.error("Briefing generation failed: %s", exc)
        # Fallback: build a basic briefing from the cluster summaries
        briefing_text = _fallback_briefing(objective, cluster_summaries, contradictions)

    # Store briefing in mission record
    await db.execute(
        "UPDATE missions SET briefing = $1 WHERE id = $2",
        briefing_text,
        mission_id,
    )

    # Publish MISSION_STATUS event
    if redis is not None:
        try:
            from streaming.channels import publish

            await publish(
                redis,
                mission_id,
                "MISSION_STATUS",
                {"status": "COMPLETE", "briefing_preview": briefing_text[:200]},
            )
        except Exception as exc:
            logger.warning("Could not publish MISSION_STATUS: %s", exc)

    logger.info(
        "Generated briefing for mission %s (%d chars)", mission_id, len(briefing_text)
    )
    return briefing_text


def _fallback_briefing(
    objective: str,
    cluster_summaries: list[ClusterSummary],
    contradictions: list[dict[str, Any]],
) -> str:
    """Build a basic briefing without LLM when Nova Lite is unavailable."""
    lines = [
        "# Intelligence Briefing\n",
        f"**Objective:** {objective}\n",
        "## Key Findings\n",
    ]
    for cs in cluster_summaries:
        lines.append(f"### {cs.theme} ({cs.evidence_count} findings)")
        for claim in cs.top_claims:
            lines.append(f"- {claim}")
        lines.append("")

    if contradictions:
        lines.append("## Contradictions")
        for c in contradictions:
            lines.append(f"- {c.get('description', 'Contradiction detected')}")
    else:
        lines.append("## Contradictions\nNone detected.")

    return "\n".join(lines)
