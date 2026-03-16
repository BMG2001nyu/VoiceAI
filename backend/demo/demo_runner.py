"""Demo-mode agent runner — simulates browser agents using mock evidence.

When DEMO_MODE=true, the planning loop spawns these lightweight coroutines
instead of real browser agents. Each coroutine:

1. Publishes an AGENT_UPDATE (BROWSING) event.
2. Sleeps 2-4 seconds to simulate browsing.
3. Picks a mock evidence item from demo/mock_evidence.json.
4. Inserts it into Postgres via the evidence repository.
5. Publishes EVIDENCE_FOUND + TIMELINE_EVENT events to Redis.
6. Transitions through REPORTING → IDLE with appropriate delays.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

# Resolve the mock evidence file relative to the repo root.
_MOCK_EVIDENCE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "demo" / "mock_evidence.json"
)

_mock_evidence_cache: list[dict[str, Any]] | None = None

# Default site URLs per agent for UI display
_AGENT_SITE_URLS: dict[str, str] = {
    "agent_0": "company-website.com",
    "agent_1": "techcrunch.com",
    "agent_2": "reddit.com/r/technology",
    "agent_3": "github.com",
    "agent_4": "crunchbase.com",
    "agent_5": "news.google.com",
}


def _agent_site_url(agent_id: str) -> str:
    """Return a representative site URL for an agent."""
    return _AGENT_SITE_URLS.get(agent_id, "web-search.ai")


def _load_mock_evidence() -> list[dict[str, Any]]:
    """Load and cache mock evidence from the JSON file."""
    global _mock_evidence_cache
    if _mock_evidence_cache is not None:
        return _mock_evidence_cache

    try:
        raw = _MOCK_EVIDENCE_PATH.read_text(encoding="utf-8")
        _mock_evidence_cache = json.loads(raw)
    except Exception as exc:
        logger.error("Failed to load mock evidence from %s: %s", _MOCK_EVIDENCE_PATH, exc)
        _mock_evidence_cache = []

    return _mock_evidence_cache


# ── Dynamic evidence templates (keyed by agent_type) ────────────────────────

_EVIDENCE_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "OFFICIAL_SITE": [
        {
            "claim": "Official documentation highlights {topic} as a key focus area",
            "summary": "The official website provides detailed information about {topic}, including product features, use cases, and technical specifications.",
            "source_url": "https://{domain}/about",
            "snippet": "According to the official site, {topic} represents a significant strategic priority with multiple ongoing initiatives.",
            "theme": "Product & Strategy",
        },
        {
            "claim": "{topic} has a comprehensive public-facing knowledge base",
            "summary": "Analysis of the official site reveals extensive documentation, API references, and developer guides related to {topic}.",
            "source_url": "https://{domain}/docs",
            "snippet": "The documentation portal includes 200+ pages covering architecture, best practices, and integration guides for {topic}.",
            "theme": "Technical Documentation",
        },
    ],
    "NEWS_BLOG": [
        {
            "claim": "Recent coverage positions {topic} as a market leader in its category",
            "summary": "TechCrunch and VentureBeat have published multiple articles in the past 3 months covering {topic}'s growth and market impact.",
            "source_url": "https://techcrunch.com/tag/{slug}",
            "snippet": "Industry analysts project {topic} will capture significant market share in the coming year based on current trajectory.",
            "theme": "Market Position",
        },
        {
            "claim": "Blog posts reveal upcoming product roadmap for {topic}",
            "summary": "Engineering blog posts outline new features and capabilities being developed for {topic}, including performance improvements and new integrations.",
            "source_url": "https://blog.example.com/{slug}",
            "snippet": "The engineering team announced three major initiatives related to {topic} expected to ship in the next quarter.",
            "theme": "Product Roadmap",
        },
    ],
    "REDDIT_HN": [
        {
            "claim": "Community sentiment around {topic} is predominantly positive with specific criticisms",
            "summary": "Analysis of Reddit and Hacker News discussions reveals strong enthusiasm for {topic}, though users cite areas for improvement including pricing and documentation gaps.",
            "source_url": "https://news.ycombinator.com/item?id={rand_id}",
            "snippet": "HN user: '{topic} has been a game-changer for our team, though the learning curve was steeper than expected.'",
            "theme": "Community Sentiment",
        },
        {
            "claim": "Developers report mixed experiences with {topic} adoption",
            "summary": "Reddit threads in r/programming and r/technology show developers sharing both success stories and challenges when adopting {topic}.",
            "source_url": "https://reddit.com/r/programming/comments/{rand_id}",
            "snippet": "Multiple threads discuss best practices for {topic}, with power users offering workarounds for common pain points.",
            "theme": "Developer Experience",
        },
    ],
    "GITHUB": [
        {
            "claim": "{topic} ecosystem shows strong open-source activity with high contributor engagement",
            "summary": "GitHub analysis reveals active repositories related to {topic} with consistent commit history, growing star counts, and diverse contributor base.",
            "source_url": "https://github.com/topics/{slug}",
            "snippet": "Top repositories related to {topic} average 500+ stars and 30+ contributors, with weekly commit activity.",
            "theme": "Open Source Ecosystem",
        },
        {
            "claim": "Technical analysis shows {topic} code quality and architecture patterns",
            "summary": "Review of GitHub repositories reveals well-structured codebases with comprehensive test coverage and modern architecture patterns.",
            "source_url": "https://github.com/search?q={slug}",
            "snippet": "Code analysis of {topic}-related repos shows 85%+ test coverage and consistent use of CI/CD pipelines.",
            "theme": "Technical Quality",
        },
    ],
    "FINANCIAL": [
        {
            "claim": "{topic} has attracted significant investment and shows strong financial indicators",
            "summary": "Crunchbase and SEC data reveal substantial funding rounds and financial metrics for {topic}, indicating strong market confidence.",
            "source_url": "https://crunchbase.com/organization/{slug}",
            "snippet": "Financial data shows {topic} has raised substantial capital with growing revenue metrics and expanding market presence.",
            "theme": "Financial Analysis",
        },
        {
            "claim": "Market analysis shows competitive positioning for {topic}",
            "summary": "Financial reports and market research indicate {topic} is well-positioned against competitors with differentiated offerings.",
            "source_url": "https://pitchbook.com/profiles/{slug}",
            "snippet": "Competitive analysis places {topic} in the top tier of its category based on growth rate, retention, and market penetration.",
            "theme": "Competitive Landscape",
        },
    ],
    "RECENT_NEWS": [
        {
            "claim": "Breaking developments show {topic} expanding into new areas",
            "summary": "Recent news coverage from the past 6 months highlights significant announcements and strategic moves related to {topic}.",
            "source_url": "https://reuters.com/technology/{slug}",
            "snippet": "Sources report {topic} is actively expanding its capabilities with new partnerships and product launches announced this quarter.",
            "theme": "Recent Developments",
        },
        {
            "claim": "Industry trends suggest growing importance of {topic}",
            "summary": "Recent analyst reports and industry publications project increasing relevance and adoption of {topic} across enterprise markets.",
            "source_url": "https://bloomberg.com/news/{slug}",
            "snippet": "Analysts predict {topic} will see accelerated adoption driven by market demand and technological maturation.",
            "theme": "Industry Trends",
        },
    ],
}


def _extract_topic(task_description: str) -> str:
    """Extract the core topic from a task description."""
    # Remove common prefixes from the demo task graph
    prefixes = [
        "Search official company websites for ",
        "Find recent news and blog posts about ",
        "Scan Reddit and Hacker News for sentiment on ",
        "Analyze GitHub repos and technical footprint for ",
        "Research financial data and funding history for ",
        "Find breaking news from last 6 months about ",
        "Research ",
        "Investigate ",
        "Analyze ",
    ]
    topic = task_description
    for prefix in prefixes:
        if topic.lower().startswith(prefix.lower()):
            topic = topic[len(prefix):]
            break
    return topic.strip()


def _generate_evidence(
    agent_id: str,
    agent_type: str,
    task_description: str,
) -> dict[str, Any]:
    """Generate a context-aware evidence item based on the actual objective."""
    topic = _extract_topic(task_description)
    slug = topic.lower().replace(" ", "-").replace("'", "")[:40]
    domain = slug.split("-")[0] + ".com" if slug else "example.com"
    rand_id = str(random.randint(10000000, 99999999))

    templates = _EVIDENCE_TEMPLATES.get(agent_type, _EVIDENCE_TEMPLATES["OFFICIAL_SITE"])
    template = random.choice(templates)

    return {
        "agent_id": agent_id,
        "claim": template["claim"].format(topic=topic, domain=domain, slug=slug, rand_id=rand_id),
        "summary": template["summary"].format(topic=topic, domain=domain, slug=slug, rand_id=rand_id),
        "source_url": template["source_url"].format(topic=topic, domain=domain, slug=slug, rand_id=rand_id),
        "snippet": template["snippet"].format(topic=topic, domain=domain, slug=slug, rand_id=rand_id),
        "theme": template["theme"],
        "confidence": round(random.uniform(0.65, 0.95), 2),
    }


async def run_demo_agent(
    agent_id: str,
    task_description: str,
    mission_id: str,
    db: asyncpg.Pool,
    redis: Any,
    agent_type: str = "OFFICIAL_SITE",
) -> None:
    """Simulate a single browser-agent task cycle in demo mode.

    Args:
        agent_id: The agent performing the task (e.g. "agent_0").
        task_description: Human-readable task objective.
        mission_id: UUID of the mission.
        db: asyncpg connection pool.
        redis: Redis client.
        agent_type: Agent type (e.g. OFFICIAL_SITE, NEWS_BLOG).
    """
    from agents.pool import update_agent_status
    from streaming.channels import (
        publish_agent_update,
        publish_timeline_event,
        publish,
    )
    from evidence.repository import insert_evidence
    from evidence.scoring import compute_confidence

    now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

    # Derive a site_url from the agent_id for UI display
    site_url = _agent_site_url(agent_id)

    try:
        # ── 0. ASSIGNED ───────────────────────────────────────────────────
        await update_agent_status(redis, agent_id, "ASSIGNED")
        await publish_agent_update(
            redis,
            mission_id,
            {
                "agent_id": agent_id,
                "status": "ASSIGNED",
                "objective": task_description,
                "site_url": site_url,
                "timestamp": now_iso(),
            },
        )
        await publish_timeline_event(
            redis,
            mission_id,
            {
                "id": str(uuid.uuid4()),
                "type": "agent_assigned",
                "description": f"{agent_id} assigned: {task_description[:80]}",
                "timestamp": now_iso(),
                "payload": {"agent_id": agent_id},
            },
        )
        await asyncio.sleep(random.uniform(1.0, 2.0))

        # ── 1. BROWSING ──────────────────────────────────────────────────
        await update_agent_status(redis, agent_id, "BROWSING")
        await publish_agent_update(
            redis,
            mission_id,
            {
                "agent_id": agent_id,
                "status": "BROWSING",
                "objective": task_description,
                "site_url": site_url,
                "timestamp": now_iso(),
            },
        )
        await publish_timeline_event(
            redis,
            mission_id,
            {
                "id": str(uuid.uuid4()),
                "type": "agent_browsing",
                "description": f"{agent_id} started browsing: {task_description[:80]}",
                "timestamp": now_iso(),
                "payload": {"agent_id": agent_id},
            },
        )

        # ── 2. Simulate browsing delay ───────────────────────────────────
        await asyncio.sleep(random.uniform(4.0, 8.0))

        # ── 3. Generate evidence based on actual objective ──────────────
        evidence_template = _generate_evidence(agent_id, agent_type, task_description)

        # ── 4. Insert evidence into DB ───────────────────────────────────
        confidence = compute_confidence(
            evidence_template.get("source_url", ""),
            evidence_template.get("snippet", ""),
        )

        row = await insert_evidence(
            db,
            mission_id=mission_id,
            agent_id=agent_id,
            claim=evidence_template["claim"],
            summary=evidence_template.get("summary", ""),
            source_url=evidence_template.get("source_url", "https://example.com"),
            snippet=evidence_template.get("snippet", ""),
            confidence=confidence,
            novelty=round(random.uniform(0.5, 1.0), 2),
            theme=evidence_template.get("theme"),
        )

        # ── 5. Publish EVIDENCE_FOUND ────────────────────────────────────
        payload = dict(row)
        ts_iso = payload["timestamp"].isoformat()
        payload["timestamp"] = ts_iso
        payload["created_at"] = ts_iso
        await publish(redis, mission_id, "EVIDENCE_FOUND", payload)

        # ── 6. Publish TIMELINE_EVENT ────────────────────────────────────
        await publish_timeline_event(
            redis,
            mission_id,
            {
                "id": str(uuid.uuid4()),
                "type": "evidence_found",
                "description": (
                    f"{agent_id} found evidence: {evidence_template['claim'][:60]}"
                ),
                "timestamp": now_iso(),
                "payload": {
                    "agent_id": agent_id,
                    "evidence_id": row["id"],
                    "theme": evidence_template.get("theme", ""),
                },
            },
        )

        logger.info(
            "Demo agent %s produced evidence %s for mission %s",
            agent_id,
            row["id"],
            mission_id[:8],
        )

        # ── 7. REPORTING ─────────────────────────────────────────────────
        await update_agent_status(redis, agent_id, "REPORTING")
        await publish_agent_update(
            redis,
            mission_id,
            {
                "agent_id": agent_id,
                "status": "REPORTING",
                "objective": task_description,
                "site_url": site_url,
                "timestamp": now_iso(),
            },
        )
        await asyncio.sleep(random.uniform(2.0, 3.0))

    except asyncio.CancelledError:
        logger.info("Demo agent %s cancelled", agent_id)
        raise
    except Exception:
        logger.exception("Demo agent %s error", agent_id)
    finally:
        # ── 8. IDLE ──────────────────────────────────────────────────────
        await _release(
            redis, agent_id, mission_id, publish_agent_update, now_iso,
            task_description=task_description, site_url=site_url,
        )


async def _release(
    redis: Any,
    agent_id: str,
    mission_id: str,
    publish_agent_update: Any,
    now_iso: Any,
    task_description: str = "",
    site_url: str = "",
) -> None:
    """Release the agent back to IDLE and publish the update."""
    from agents.pool import release_agent

    try:
        await release_agent(redis, agent_id)
        await publish_agent_update(
            redis,
            mission_id,
            {
                "agent_id": agent_id,
                "status": "IDLE",
                "objective": task_description,
                "site_url": site_url,
                "timestamp": now_iso(),
            },
        )
    except Exception:
        logger.exception("Failed to release demo agent %s", agent_id)


async def run_demo_agents_batch(
    assignments: list,
    mission_id: str,
    db: asyncpg.Pool,
    redis: Any,
) -> list[asyncio.Task]:
    """Spawn demo-agent tasks for a batch of assignments.

    Args:
        assignments: List of AssignAction objects from the assignment algorithm.
        mission_id: UUID of the mission.
        db: asyncpg connection pool.
        redis: Redis client.

    Returns:
        List of asyncio.Task handles (caller can await or cancel).
    """
    tasks: list[asyncio.Task] = []
    for action in assignments:
        task = asyncio.create_task(
            run_demo_agent(
                agent_id=action.agent_id,
                task_description=action.objective,
                mission_id=mission_id,
                db=db,
                redis=redis,
                agent_type=action.agent_type,
            ),
            name=f"demo:{action.agent_id}:{mission_id[:8]}",
        )
        tasks.append(task)

    if tasks:
        logger.info(
            "Spawned %d demo agents for mission %s",
            len(tasks),
            mission_id[:8],
        )

    return tasks
