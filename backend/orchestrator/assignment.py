"""Agent-to-task assignment algorithm.

Greedy priority-based assignment: given available tasks and idle agents,
pair them optimally. Prefers matching agent types when possible.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from agents.pool import get_idle_agents

logger = logging.getLogger(__name__)

# Agent type preferences — maps agent_type to preferred agent indices
# For demo: any agent can handle any type (round-robin sufficient)
_TYPE_PREFERENCES: dict[str, list[int]] = {
    "OFFICIAL_SITE": [0],
    "NEWS_BLOG": [1],
    "REDDIT_HN": [2],
    "GITHUB": [3],
    "FINANCIAL": [4],
    "RECENT_NEWS": [5],
}


@dataclass
class AssignAction:
    """A single agent-to-task assignment."""

    agent_id: str
    task_id: str
    objective: str
    agent_type: str
    constraints: dict[str, Any]


async def assign_tasks(
    available_tasks: list,  # list[TaskNode]
    redis: Any,
    pool_size: int = 6,
) -> list[AssignAction]:
    """Assign available tasks to idle agents using greedy priority matching.

    Algorithm:
    1. Get list of idle agents
    2. Sort tasks by priority (DESC), then by creation time (ASC)
    3. For each task, prefer an agent whose index matches the agent type
    4. If preferred agent is busy, assign to any idle agent

    Args:
        available_tasks: Tasks ready for assignment (from get_available_tasks).
        redis: aioredis client.
        pool_size: Size of the agent pool.

    Returns:
        List of AssignAction objects (one per assignment).
    """
    idle_agents = await get_idle_agents(redis, pool_size)

    if not idle_agents or not available_tasks:
        return []

    # Sort tasks: highest priority first, oldest first
    sorted_tasks = sorted(
        available_tasks,
        key=lambda t: (-t.priority, t.created_at),
    )

    remaining_agents = list(idle_agents)
    actions: list[AssignAction] = []

    for task in sorted_tasks:
        if not remaining_agents:
            break

        # Try to find preferred agent for this type
        agent_id = _pick_preferred_agent(task.agent_type, remaining_agents)

        if agent_id is None:
            # No preferred agent available — take first idle
            agent_id = remaining_agents[0]

        remaining_agents.remove(agent_id)

        constraints = _build_constraints(task.agent_type)

        actions.append(
            AssignAction(
                agent_id=agent_id,
                task_id=task.id,
                objective=task.description,
                agent_type=task.agent_type,
                constraints=constraints,
            )
        )

        logger.info(
            "Assigned %s → %s (type=%s, priority=%d)",
            agent_id,
            task.id[:8],
            task.agent_type,
            task.priority,
        )

    return actions


def _pick_preferred_agent(
    agent_type: str,
    available: list[str],
) -> str | None:
    """Pick the preferred agent for a given type, if available."""
    preferred_indices = _TYPE_PREFERENCES.get(agent_type, [])
    for idx in preferred_indices:
        preferred_id = f"agent_{idx}"
        if preferred_id in available:
            return preferred_id
    return None


def _build_constraints(agent_type: str) -> dict[str, Any]:
    """Build task constraints based on agent type."""
    base: dict[str, Any] = {"timeout_s": 120}

    type_urls = {
        "REDDIT_HN": "https://www.reddit.com",
        "GITHUB": "https://github.com",
        "FINANCIAL": "https://www.crunchbase.com",
        "RECENT_NEWS": "https://news.google.com",
    }

    if agent_type in type_urls:
        base["starting_url"] = type_urls[agent_type]

    return base
