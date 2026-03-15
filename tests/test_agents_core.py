"""Unit tests for Mission Control core agent modules.

Covers: prompt loader, schemas, task graph, assignment, VAD, and BrowserResult.
All tests are self-contained — no external services required.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure project root is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ===================================================================
# 1. Prompts loader
# ===================================================================

class TestPromptsLoader:
    """Tests for agents.prompts module."""

    def test_available_prompts_returns_seven(self) -> None:
        from agents.prompts import available_prompts

        prompts = available_prompts()
        assert len(prompts) == 7, f"Expected 7 prompt types, got {len(prompts)}: {prompts}"

    def test_load_official_site_prompt(self) -> None:
        from agents.prompts import load_prompt

        text = load_prompt("OFFICIAL_SITE")
        assert isinstance(text, str)
        assert len(text) > 0
        assert "research agent" in text.lower(), (
            "OFFICIAL_SITE prompt should contain 'research agent'"
        )

    def test_load_nonexistent_prompt_raises(self) -> None:
        from agents.prompts import load_prompt

        with pytest.raises(FileNotFoundError):
            load_prompt("NONEXISTENT")

    def test_each_prompt_loads_and_has_min_length(self) -> None:
        from agents.prompts import available_prompts, load_prompt

        for prompt_type in available_prompts():
            text = load_prompt(prompt_type)
            assert len(text) > 50, (
                f"Prompt '{prompt_type}' is too short ({len(text)} chars)"
            )


# ===================================================================
# 2. Schemas
# ===================================================================

class TestSchemas:
    """Tests for agents.schemas module."""

    def test_agent_command_creation(self) -> None:
        from agents.schemas import AgentCommand, CommandType

        cmd = AgentCommand(
            command_type=CommandType.ASSIGN,
            agent_id="agent_0",
            task_id="task-123",
            mission_id="mission-abc",
            objective="Research Sequoia",
            agent_type="OFFICIAL_SITE",
            constraints={"timeout_s": 120},
        )
        assert cmd.command_type == CommandType.ASSIGN
        assert cmd.agent_id == "agent_0"
        assert cmd.task_id == "task-123"
        assert cmd.mission_id == "mission-abc"
        assert cmd.objective == "Research Sequoia"
        assert cmd.agent_type == "OFFICIAL_SITE"
        assert cmd.constraints == {"timeout_s": 120}

    def test_agent_command_json_roundtrip(self) -> None:
        from agents.schemas import AgentCommand, CommandType

        original = AgentCommand(
            command_type=CommandType.REDIRECT,
            agent_id="agent_2",
            task_id="task-456",
            objective="Redirect to news",
            constraints={"starting_url": "https://example.com"},
        )
        json_str = original.model_dump_json()
        restored = AgentCommand.model_validate_json(json_str)
        assert restored == original

    def test_command_type_members(self) -> None:
        from agents.schemas import CommandType

        assert hasattr(CommandType, "ASSIGN")
        assert hasattr(CommandType, "REDIRECT")
        assert hasattr(CommandType, "STOP")
        assert len(CommandType) == 3

    def test_agent_status_members(self) -> None:
        from agents.schemas import AgentStatus

        assert hasattr(AgentStatus, "IDLE")
        assert hasattr(AgentStatus, "ASSIGNED")
        assert hasattr(AgentStatus, "BROWSING")
        assert hasattr(AgentStatus, "REPORTING")
        assert len(AgentStatus) == 4


# ===================================================================
# 3. TaskGraph
# ===================================================================

class TestTaskGraph:
    """Tests for backend.orchestrator.task_graph module."""

    def test_build_task_graph(self) -> None:
        from backend.orchestrator.task_graph import build_task_graph

        plan = [
            {"id": "t1", "description": "Task one", "agent_type": "OFFICIAL_SITE", "priority": 10},
            {"id": "t2", "description": "Task two", "agent_type": "NEWS_BLOG", "priority": 5},
        ]
        nodes = build_task_graph(plan)
        assert len(nodes) == 2
        assert nodes[0].id == "t1"
        assert nodes[0].description == "Task one"
        assert nodes[0].status == "PENDING"
        assert nodes[1].agent_type == "NEWS_BLOG"

    def test_get_available_tasks_returns_pending_with_deps_met(self) -> None:
        from backend.orchestrator.task_graph import TaskNode, get_available_tasks

        tasks = [
            TaskNode(id="t1", description="A", agent_type="X", priority=5, status="DONE"),
            TaskNode(id="t2", description="B", agent_type="X", priority=8, status="PENDING", dependencies=["t1"]),
            TaskNode(id="t3", description="C", agent_type="X", priority=3, status="PENDING", dependencies=[]),
        ]
        available = get_available_tasks(tasks)
        assert len(available) == 2
        # t2 (priority 8) should come before t3 (priority 3)
        assert available[0].id == "t2"
        assert available[1].id == "t3"

    def test_get_available_tasks_sorted_by_priority_desc(self) -> None:
        from backend.orchestrator.task_graph import TaskNode, get_available_tasks

        tasks = [
            TaskNode(id="a", description="low", agent_type="X", priority=1, status="PENDING"),
            TaskNode(id="b", description="high", agent_type="X", priority=10, status="PENDING"),
            TaskNode(id="c", description="mid", agent_type="X", priority=5, status="PENDING"),
        ]
        available = get_available_tasks(tasks)
        priorities = [t.priority for t in available]
        assert priorities == [10, 5, 1]

    def test_tasks_with_unmet_deps_not_available(self) -> None:
        from backend.orchestrator.task_graph import TaskNode, get_available_tasks

        tasks = [
            TaskNode(id="t1", description="A", agent_type="X", priority=5, status="PENDING"),
            TaskNode(id="t2", description="B", agent_type="X", priority=8, status="PENDING", dependencies=["t1"]),
        ]
        available = get_available_tasks(tasks)
        # t2 depends on t1 which is PENDING (not DONE), so only t1 is available
        assert len(available) == 1
        assert available[0].id == "t1"

    def test_all_tasks_complete_true(self) -> None:
        from backend.orchestrator.task_graph import TaskNode, all_tasks_complete

        tasks = [
            TaskNode(id="t1", description="A", agent_type="X", status="DONE"),
            TaskNode(id="t2", description="B", agent_type="X", status="FAILED"),
        ]
        assert all_tasks_complete(tasks) is True

    def test_all_tasks_complete_false(self) -> None:
        from backend.orchestrator.task_graph import TaskNode, all_tasks_complete

        tasks = [
            TaskNode(id="t1", description="A", agent_type="X", status="DONE"),
            TaskNode(id="t2", description="B", agent_type="X", status="PENDING"),
        ]
        assert all_tasks_complete(tasks) is False

    def test_get_task_summary(self) -> None:
        from backend.orchestrator.task_graph import TaskNode, get_task_summary

        tasks = [
            TaskNode(id="t1", description="A", agent_type="X", status="DONE"),
            TaskNode(id="t2", description="B", agent_type="X", status="DONE"),
            TaskNode(id="t3", description="C", agent_type="X", status="PENDING"),
            TaskNode(id="t4", description="D", agent_type="X", status="FAILED"),
        ]
        summary = get_task_summary(tasks)
        assert summary == {"DONE": 2, "PENDING": 1, "FAILED": 1}


# ===================================================================
# 4. Assignment (mock redis)
# ===================================================================

class TestAssignment:
    """Tests for backend.orchestrator.assignment module."""

    def test_assign_action_creation(self) -> None:
        from backend.orchestrator.assignment import AssignAction

        action = AssignAction(
            agent_id="agent_0",
            task_id="task-1",
            objective="Research target",
            agent_type="OFFICIAL_SITE",
            constraints={"timeout_s": 120},
        )
        assert action.agent_id == "agent_0"
        assert action.task_id == "task-1"
        assert action.objective == "Research target"
        assert action.agent_type == "OFFICIAL_SITE"
        assert action.constraints == {"timeout_s": 120}

    def test_pick_preferred_agent(self) -> None:
        from backend.orchestrator.assignment import _pick_preferred_agent

        available = ["agent_0", "agent_1", "agent_2", "agent_3"]
        assert _pick_preferred_agent("OFFICIAL_SITE", available) == "agent_0"
        assert _pick_preferred_agent("NEWS_BLOG", available) == "agent_1"
        assert _pick_preferred_agent("REDDIT_HN", available) == "agent_2"
        assert _pick_preferred_agent("GITHUB", available) == "agent_3"

    def test_pick_preferred_agent_not_available(self) -> None:
        from backend.orchestrator.assignment import _pick_preferred_agent

        available = ["agent_2", "agent_3"]
        # agent_0 is preferred for OFFICIAL_SITE but not in available list
        assert _pick_preferred_agent("OFFICIAL_SITE", available) is None

    def test_build_constraints(self) -> None:
        from backend.orchestrator.assignment import _build_constraints

        reddit = _build_constraints("REDDIT_HN")
        assert reddit["timeout_s"] == 120
        assert reddit["starting_url"] == "https://www.reddit.com"

        github = _build_constraints("GITHUB")
        assert github["starting_url"] == "https://github.com"

        official = _build_constraints("OFFICIAL_SITE")
        assert official["timeout_s"] == 120
        assert "starting_url" not in official

    @pytest.mark.asyncio
    async def test_assign_tasks_with_mocked_pool(self) -> None:
        from backend.orchestrator.task_graph import TaskNode
        from backend.orchestrator.assignment import assign_tasks

        tasks = [
            TaskNode(id="t1", description="Official research", agent_type="OFFICIAL_SITE", priority=10, created_at=1.0),
            TaskNode(id="t2", description="Reddit research", agent_type="REDDIT_HN", priority=5, created_at=2.0),
        ]

        mock_redis = AsyncMock()

        with patch(
            "backend.orchestrator.assignment.get_idle_agents",
            new_callable=AsyncMock,
            return_value=["agent_0", "agent_1", "agent_2"],
        ):
            actions = await assign_tasks(tasks, mock_redis, pool_size=6)

        assert len(actions) == 2
        # t1 (priority 10) assigned first to preferred agent_0
        assert actions[0].task_id == "t1"
        assert actions[0].agent_id == "agent_0"
        # t2 (priority 5) assigned to preferred agent_2 (REDDIT_HN)
        assert actions[1].task_id == "t2"
        assert actions[1].agent_id == "agent_2"

    @pytest.mark.asyncio
    async def test_assign_tasks_empty_idle(self) -> None:
        from backend.orchestrator.task_graph import TaskNode
        from backend.orchestrator.assignment import assign_tasks

        tasks = [
            TaskNode(id="t1", description="Something", agent_type="OFFICIAL_SITE", priority=5),
        ]
        mock_redis = AsyncMock()

        with patch(
            "backend.orchestrator.assignment.get_idle_agents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            actions = await assign_tasks(tasks, mock_redis)

        assert actions == []


# ===================================================================
# 5. VAD (Voice Activity Detector)
# ===================================================================

class TestVAD:
    """Tests for backend.gateway.vad module."""

    def test_frame_size_constant(self) -> None:
        from backend.gateway.vad import FRAME_SIZE

        assert FRAME_SIZE == 640

    def test_passthrough_mode_yields_input_unchanged(self) -> None:
        from backend.gateway.vad import VoiceActivityDetector

        vad = VoiceActivityDetector()
        # Force passthrough by marking as initialized without webrtcvad
        vad._initialized = True
        vad._vad = None

        test_audio = b"\x00" * 640
        chunks = list(vad.process(test_audio))
        assert len(chunks) == 1
        assert chunks[0] == test_audio

    def test_flush_returns_none_when_empty(self) -> None:
        from backend.gateway.vad import VoiceActivityDetector

        vad = VoiceActivityDetector()
        assert vad.flush() is None

    def test_reset_clears_state(self) -> None:
        from backend.gateway.vad import VoiceActivityDetector

        vad = VoiceActivityDetector()
        # Manually add data to buffers
        vad._speech_buffer.extend(b"\x01\x02\x03")
        vad._pre_buffer.append(b"\x04\x05")
        vad._silent_frame_count = 10
        vad._in_speech = True

        vad.reset()

        assert len(vad._speech_buffer) == 0
        assert len(vad._pre_buffer) == 0
        assert vad._silent_frame_count == 0
        assert vad._in_speech is False


# ===================================================================
# 6. BrowserResult
# ===================================================================

class TestBrowserResult:
    """Tests for agents.browser_session.BrowserResult."""

    def test_default_creation(self) -> None:
        from agents.browser_session import BrowserResult

        result = BrowserResult()
        assert result.extracted_text == ""
        assert result.source_url == ""
        assert result.screenshot_base64 is None
        assert result.success is True
        assert result.error is None
        assert result.metadata == {}

    def test_failed_result_with_error(self) -> None:
        from agents.browser_session import BrowserResult

        result = BrowserResult(
            success=False,
            error="Connection timeout",
            source_url="https://example.com",
        )
        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.source_url == "https://example.com"
        assert result.extracted_text == ""
