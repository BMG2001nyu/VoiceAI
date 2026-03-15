"""CloudWatch metrics emission for Mission Control.

Provides async-safe helpers to emit counters, timers, and gauges to
CloudWatch under the ``MissionControl`` namespace.  In demo mode,
metrics are logged to stdout instead of calling the CloudWatch API.

A background buffer batches ``PutMetricData`` calls — flushing every
60 seconds or when 20 data-points accumulate.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import boto3
import structlog

from config import settings

logger = structlog.get_logger(__name__)

_NAMESPACE = "MissionControl"
_FLUSH_INTERVAL_S = 60
_FLUSH_THRESHOLD = 20

# Module-level state — initialised lazily.
_buffer: list[dict[str, Any]] = []
_buffer_lock: asyncio.Lock | None = None
_flush_task: asyncio.Task[None] | None = None
_executor = ThreadPoolExecutor(max_workers=1)
_cw_client: Any | None = None


def _get_lock() -> asyncio.Lock:
    """Return (and lazily create) the module-level async lock."""
    global _buffer_lock  # noqa: PLW0603
    if _buffer_lock is None:
        _buffer_lock = asyncio.Lock()
    return _buffer_lock


def _get_cw_client() -> Any:
    global _cw_client  # noqa: PLW0603
    if _cw_client is None:
        _cw_client = boto3.client("cloudwatch", region_name=settings.aws_region)
    return _cw_client


def _build_dimensions(dimensions: dict[str, str] | None) -> list[dict[str, str]]:
    if not dimensions:
        return []
    return [{"Name": k, "Value": str(v)} for k, v in dimensions.items()]


def _build_datum(
    metric_name: str,
    value: float,
    unit: str,
    dimensions: dict[str, str] | None,
) -> dict[str, Any]:
    datum: dict[str, Any] = {
        "MetricName": metric_name,
        "Value": value,
        "Unit": unit,
    }
    dims = _build_dimensions(dimensions)
    if dims:
        datum["Dimensions"] = dims
    return datum


# ── Public helpers ───────────────────────────────────────────────────────────


async def emit_counter(
    metric_name: str,
    value: float = 1.0,
    dimensions: dict[str, str] | None = None,
) -> None:
    """Emit a Count metric."""
    await _enqueue(_build_datum(metric_name, value, "Count", dimensions))


async def emit_timer(
    metric_name: str,
    seconds: float,
    dimensions: dict[str, str] | None = None,
) -> None:
    """Emit a Seconds metric (timer)."""
    await _enqueue(_build_datum(metric_name, seconds, "Seconds", dimensions))


async def emit_gauge(
    metric_name: str,
    value: float,
    dimensions: dict[str, str] | None = None,
) -> None:
    """Emit a gauge (None unit)."""
    await _enqueue(_build_datum(metric_name, value, "None", dimensions))


# ── Buffer internals ────────────────────────────────────────────────────────


async def _enqueue(datum: dict[str, Any]) -> None:
    if settings.demo_mode:
        logger.info(
            "metric_demo",
            metric_name=datum["MetricName"],
            value=datum["Value"],
            unit=datum["Unit"],
            dimensions=datum.get("Dimensions"),
        )
        return

    lock = _get_lock()
    async with lock:
        _buffer.append(datum)
        if len(_buffer) >= _FLUSH_THRESHOLD:
            await _flush_locked()

    _ensure_periodic_flush()


async def _flush_locked() -> None:
    """Flush the buffer while the lock is already held."""
    if not _buffer:
        return
    batch = list(_buffer)
    _buffer.clear()
    await _put_metric_data(batch)


async def flush() -> None:
    """Force-flush the buffer (call during shutdown)."""
    lock = _get_lock()
    async with lock:
        await _flush_locked()


async def _put_metric_data(data: Sequence[dict[str, Any]]) -> None:
    """Send metric data to CloudWatch via ``run_in_executor``."""
    loop = asyncio.get_running_loop()
    try:
        client = _get_cw_client()
        # CloudWatch supports up to 1000 metric data-points per call.
        for i in range(0, len(data), 1000):
            chunk = list(data[i : i + 1000])
            await loop.run_in_executor(
                _executor,
                lambda c=chunk: client.put_metric_data(  # type: ignore[misc]
                    Namespace=_NAMESPACE,
                    MetricData=c,
                ),
            )
    except Exception:
        logger.warning("cloudwatch_put_failed", count=len(data), exc_info=True)


def _ensure_periodic_flush() -> None:
    global _flush_task  # noqa: PLW0603
    if _flush_task is not None and not _flush_task.done():
        return
    try:
        _flush_task = asyncio.create_task(_periodic_flush())
    except RuntimeError:
        pass


async def _periodic_flush() -> None:
    """Background task that flushes the buffer every ``_FLUSH_INTERVAL_S``."""
    while True:
        await asyncio.sleep(_FLUSH_INTERVAL_S)
        lock = _get_lock()
        async with lock:
            await _flush_locked()
