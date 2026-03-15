"""Task graph dependency resolution.

Determines which tasks are available (all dependencies satisfied) at each
planning cycle. Used by the assignment algorithm to pick tasks for idle agents.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TaskNode:
    """A single task in the mission's task graph."""
    id: str
    description: str
    agent_type: str
    priority: int = 5
    status: str = "PENDING"  # PENDING, ASSIGNED, IN_PROGRESS, DONE, FAILED
    dependencies: list[str] = field(default_factory=list)
    assigned_agent: str | None = None
    created_at: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TaskNode:
        """Create a TaskNode from a dict (e.g., from DB or Nova Lite output)."""
        return cls(
            id=str(d.get("id", "")),
            description=d.get("description", ""),
            agent_type=d.get("agent_type", "OFFICIAL_SITE"),
            priority=int(d.get("priority", 5)),
            status=d.get("status", "PENDING"),
            dependencies=d.get("dependencies", []),
            assigned_agent=d.get("assigned_agent"),
            created_at=float(d.get("created_at", 0)),
        )


def get_available_tasks(tasks: list[TaskNode]) -> list[TaskNode]:
    """Return tasks that are PENDING and have all dependencies satisfied.

    A task is available when:
    1. Its status is PENDING
    2. All tasks in its dependencies list have status DONE

    Args:
        tasks: Full list of tasks in the mission's task graph.

    Returns:
        List of TaskNode objects ready for assignment, sorted by priority DESC.
    """
    done_ids = {t.id for t in tasks if t.status == "DONE"}

    available = [
        t for t in tasks
        if t.status == "PENDING"
        and all(dep in done_ids for dep in t.dependencies)
    ]

    # Sort: highest priority first, then oldest first
    available.sort(key=lambda t: (-t.priority, t.created_at))

    logger.debug(
        "Available tasks: %d/%d (done=%d)",
        len(available), len(tasks), len(done_ids),
    )
    return available


def get_task_by_id(tasks: list[TaskNode], task_id: str) -> TaskNode | None:
    """Find a task by its ID."""
    for t in tasks:
        if t.id == task_id:
            return t
    return None


def all_tasks_complete(tasks: list[TaskNode]) -> bool:
    """Check if all tasks in the graph are DONE or FAILED."""
    return all(t.status in ("DONE", "FAILED") for t in tasks)


def get_task_summary(tasks: list[TaskNode]) -> dict[str, int]:
    """Return count of tasks by status."""
    summary: dict[str, int] = {}
    for t in tasks:
        summary[t.status] = summary.get(t.status, 0) + 1
    return summary


def build_task_graph(plan_output: list[dict[str, Any]]) -> list[TaskNode]:
    """Convert Nova Lite plan_tasks() output into a list of TaskNode objects.

    Assigns UUIDs to tasks that don't have IDs.

    Args:
        plan_output: List of task dicts from LiteClient.plan_tasks().

    Returns:
        List of TaskNode objects ready for the planning loop.
    """
    import uuid
    import time

    nodes = []
    for i, task_dict in enumerate(plan_output):
        node = TaskNode(
            id=task_dict.get("id", str(uuid.uuid4())),
            description=task_dict.get("description", f"Task {i}"),
            agent_type=task_dict.get("agent_type", "OFFICIAL_SITE"),
            priority=int(task_dict.get("priority", 5)),
            status="PENDING",
            dependencies=task_dict.get("dependencies", []),
            created_at=time.time() + i * 0.001,  # Preserve order
        )
        nodes.append(node)

    logger.info("Built task graph: %d nodes", len(nodes))
    return nodes
