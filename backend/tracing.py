"""X-Ray distributed tracing for Mission Control.

Provides a FastAPI middleware that wraps each request in an X-Ray segment
and a helper context manager for manual subsegments.

In ``DEMO_MODE`` the X-Ray recorder is replaced with a no-op so no SDK
calls are made and no daemon connection is required.
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from config import settings

logger = structlog.get_logger(__name__)

# ── Lazy X-Ray setup ────────────────────────────────────────────────────────

_recorder: Any = None
_patched = False


def _get_recorder() -> Any:
    """Return the global ``xray_recorder``, configured once."""
    global _recorder  # noqa: PLW0603
    if _recorder is not None:
        return _recorder

    from aws_xray_sdk.core import xray_recorder  # type: ignore[import-untyped]

    xray_recorder.configure(
        service="MissionControl",
        sampling=True,
        context_missing="LOG_ERROR",
        daemon_address="127.0.0.1:2000",
    )
    _recorder = xray_recorder
    return _recorder


def _patch_libraries() -> None:
    """Patch supported libraries for automatic subsegment capture."""
    global _patched  # noqa: PLW0603
    if _patched:
        return
    try:
        from aws_xray_sdk.core import patch  # type: ignore[import-untyped]

        patch(["boto3", "requests"])
    except Exception:
        logger.warning("xray_patch_failed", exc_info=True)
    _patched = True


# ── Middleware ───────────────────────────────────────────────────────────────


class XRayMiddleware(BaseHTTPMiddleware):
    """Create an X-Ray segment for every HTTP request."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        recorder = _get_recorder()
        segment_name = f"{request.method} {request.url.path}"
        segment = recorder.begin_segment(segment_name)

        # Annotate with mission / agent IDs when present in the path.
        path_params: dict[str, Any] = request.path_params or {}
        if "mission_id" in path_params:
            segment.put_annotation("mission_id", str(path_params["mission_id"]))
        if "agent_id" in path_params:
            segment.put_annotation("agent_id", str(path_params["agent_id"]))

        try:
            response = await call_next(request)
            segment.put_http_meta(
                "response",
                {"status": response.status_code},
            )
            return response
        except Exception as exc:
            segment.add_exception(exc, True)
            raise
        finally:
            recorder.end_segment()


# ── Manual subsegment helper ────────────────────────────────────────────────


@contextlib.contextmanager
def trace_subsegment(name: str, **annotations: str) -> Generator[Any, None, None]:
    """Open (and auto-close) an X-Ray subsegment.

    In demo mode this is a no-op context manager.

    Usage::

        with trace_subsegment("fetch_evidence", mission_id=mid):
            ...
    """
    if settings.demo_mode:
        yield None
        return

    recorder = _get_recorder()
    subsegment = recorder.begin_subsegment(name)
    try:
        for key, val in annotations.items():
            subsegment.put_annotation(key, val)
        yield subsegment
    except Exception as exc:
        subsegment.add_exception(exc, True)
        raise
    finally:
        recorder.end_subsegment()


# ── Init helper called from main.py ─────────────────────────────────────────


def init_tracing() -> None:
    """Initialise the recorder and patch libraries.

    Called once during app startup (non-demo mode only).
    """
    _get_recorder()
    _patch_libraries()
    logger.info("xray_tracing_initialised")
