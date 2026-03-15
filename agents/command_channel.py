"""Agent command channel — Redis-based command dispatch and consumption.

The orchestrator pushes AgentCommand messages to per-agent Redis lists.
Agent workers consume commands via blocking pop (BRPOP).

Includes parallel dispatch (Task 11.3) for launching multiple agents
simultaneously using asyncio.TaskGroup.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agents.schemas import AgentCommand, CommandType

logger = logging.getLogger(__name__)


def command_queue_key(agent_id: str) -> str:
    """Redis list key for an agent's command queue."""
    return f"agent:{agent_id}:commands"


async def send_command(command: AgentCommand, redis: Any) -> None:
    """Push a command onto an agent's command queue.

    Args:
        command: The AgentCommand to send.
        redis: aioredis client.
    """
    key = command_queue_key(command.agent_id)
    payload = command.model_dump_json()
    await redis.lpush(key, payload)
    logger.info(
        "Sent %s command to %s (task=%s)",
        command.command_type, command.agent_id, command.task_id,
    )


async def receive_command(
    agent_id: str,
    redis: Any,
    timeout: int = 0,
) -> AgentCommand | None:
    """Block until a command is available for the agent.

    Args:
        agent_id: Agent ID to listen for commands.
        redis: aioredis client.
        timeout: BRPOP timeout in seconds (0 = block forever).

    Returns:
        AgentCommand if received, None on timeout.
    """
    key = command_queue_key(agent_id)
    result = await redis.brpop(key, timeout=timeout)

    if result is None:
        return None

    _, raw = result
    if isinstance(raw, bytes):
        raw = raw.decode()

    return AgentCommand.model_validate_json(raw)


async def command_listener(
    agent_id: str,
    redis: Any,
    handler: Any,  # async callable(AgentCommand)
) -> None:
    """Continuous command listener loop for an agent.

    Blocks on BRPOP and dispatches each command to the handler.
    Runs until cancelled.

    Args:
        agent_id: Agent ID to listen for.
        redis: aioredis client.
        handler: Async callable that processes each AgentCommand.
    """
    logger.info("Command listener started for %s", agent_id)
    try:
        while True:
            command = await receive_command(agent_id, redis, timeout=0)
            if command is None:
                continue

            logger.info(
                "Agent %s received %s command (task=%s)",
                agent_id, command.command_type, command.task_id,
            )

            try:
                await handler(command)
            except Exception as exc:
                logger.error(
                    "Agent %s: command handler error: %s", agent_id, exc
                )
    except asyncio.CancelledError:
        logger.info("Command listener stopped for %s", agent_id)


async def handle_command(
    command: AgentCommand,
    redis: Any,
    backend_url: str = "http://localhost:8000",
) -> None:
    """Default command handler — dispatches based on command type.

    Args:
        command: The received AgentCommand.
        redis: aioredis client.
        backend_url: Backend API base URL.
    """
    if command.command_type == CommandType.ASSIGN:
        from agents.lifecycle import run_agent_task
        await run_agent_task(
            agent_id=command.agent_id,
            redis=redis,
            mission_id=command.mission_id or "",
            task_id=command.task_id or "",
            objective=command.objective,
            agent_type=command.agent_type,
            constraints=command.constraints,
            backend_url=backend_url,
        )

    elif command.command_type == CommandType.REDIRECT:
        # Cancel current task and start new one
        from agents.pool import update_agent_status
        await update_agent_status(redis, command.agent_id, "ASSIGNED")

        from agents.lifecycle import run_agent_task
        await run_agent_task(
            agent_id=command.agent_id,
            redis=redis,
            mission_id=command.mission_id or "",
            task_id=command.task_id or "",
            objective=command.objective,
            agent_type=command.agent_type,
            constraints=command.constraints,
            backend_url=backend_url,
        )

    elif command.command_type == CommandType.STOP:
        from agents.pool import release_agent
        await release_agent(redis, command.agent_id)
        logger.info("Agent %s stopped and released", command.agent_id)


# ── Parallel Dispatch (Task 11.3) ───────────────────────────────────────────


async def dispatch_commands(
    actions: list,  # list[AssignAction] from assignment.py
    redis: Any,
    mission_id: str,
) -> int:
    """Dispatch multiple agent commands in parallel using TaskGroup.

    All commands are enqueued concurrently — does not wait for agents
    to acknowledge or complete.

    Args:
        actions: List of AssignAction from the assignment algorithm.
        redis: aioredis client.
        mission_id: Mission UUID for the commands.

    Returns:
        Number of commands successfully dispatched.
    """
    if not actions:
        return 0

    dispatched = 0

    async with asyncio.TaskGroup() as tg:
        for action in actions:
            command = AgentCommand(
                command_type=CommandType.ASSIGN,
                agent_id=action.agent_id,
                task_id=action.task_id,
                mission_id=mission_id,
                objective=action.objective,
                agent_type=action.agent_type,
                constraints=action.constraints,
            )
            tg.create_task(_dispatch_one(command, redis, action.agent_id, action.task_id))

    # If we get here, all tasks completed (TaskGroup propagates exceptions)
    dispatched = len(actions)

    logger.info(
        "Dispatched %d commands for mission %s",
        dispatched, mission_id[:8] if mission_id else "?",
    )
    return dispatched


async def _dispatch_one(
    command: AgentCommand,
    redis: Any,
    agent_id: str,
    task_id: str,
) -> None:
    """Send a single command and claim the agent atomically."""
    from agents.pool import claim_agent

    # Claim agent first
    claimed = await claim_agent(
        redis,
        agent_id,
        task_id,
        command.mission_id or "",
        command.agent_type,
    )

    if not claimed:
        logger.warning("Failed to claim %s for task %s", agent_id, task_id)
        return

    # Push command to queue
    await send_command(command, redis)


async def start_agent_workers(
    redis: Any,
    pool_size: int = 6,
    backend_url: str = "http://localhost:8000",
) -> list[asyncio.Task]:
    """Start command listener workers for all agents in the pool.

    Each worker runs as a background asyncio.Task that listens
    for commands and executes them.

    Args:
        redis: aioredis client.
        pool_size: Number of agent workers to start.
        backend_url: Backend API base URL.

    Returns:
        List of asyncio.Task objects (cancel to stop workers).
    """
    from agents.pool import init_pool

    await init_pool(redis, pool_size)

    tasks = []
    for i in range(pool_size):
        agent_id = f"agent_{i}"

        async def _handler(cmd: AgentCommand, _redis=redis, _url=backend_url) -> None:
            await handle_command(cmd, _redis, _url)

        task = asyncio.create_task(
            command_listener(agent_id, redis, _handler),
            name=f"worker:{agent_id}",
        )
        tasks.append(task)

    logger.info("Started %d agent workers", pool_size)
    return tasks
