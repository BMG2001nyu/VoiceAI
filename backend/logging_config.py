"""Structured JSON logging configuration for Mission Control.

Uses structlog for structured logging with JSON output in production
and colored console output in development.

Usage:
    from logging_config import configure_logging, get_logger
    configure_logging(level="INFO")
    logger = get_logger(__name__)
    logger.info("mission_started", mission_id="abc-123", objective="...")
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog and stdlib logging for the application.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
        json_output: If True, render as JSON (production). If False, colored console (dev).
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Quieten noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger bound to the given name."""
    return structlog.get_logger(name)


def bind_mission_context(
    mission_id: str | None = None,
    agent_id: str | None = None,
    request_id: str | None = None,
) -> None:
    """Bind correlation IDs to the current context.

    All subsequent log calls in this async context will include these fields.
    """
    ctx = {}
    if mission_id:
        ctx["mission_id"] = mission_id
    if agent_id:
        ctx["agent_id"] = agent_id
    if request_id:
        ctx["request_id"] = request_id
    if ctx:
        structlog.contextvars.bind_contextvars(**ctx)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
