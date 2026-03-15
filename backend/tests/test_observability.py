"""Tests for the observability layer — metrics and X-Ray tracing."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Metrics tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_metrics_buffer():
    """Clear the module-level buffer between tests."""
    import metrics

    metrics._buffer.clear()
    metrics._cw_client = None
    metrics._flush_task = None
    yield
    metrics._buffer.clear()


class TestMetricsDemoMode:
    """In demo mode, metrics are logged — no boto3 calls."""

    @pytest.mark.asyncio
    async def test_emit_counter_logs_in_demo_mode(self):
        with patch("metrics.settings") as mock_settings:
            mock_settings.demo_mode = True
            mock_settings.aws_region = "us-east-1"

            import metrics

            with patch.object(metrics.logger, "info") as log_spy:
                await metrics.emit_counter("mission_start_total", 1.0, {"env": "test"})
                log_spy.assert_called_once()
                call_kwargs = log_spy.call_args
                assert call_kwargs[1]["metric_name"] == "mission_start_total"
                assert call_kwargs[1]["value"] == 1.0

    @pytest.mark.asyncio
    async def test_emit_timer_logs_in_demo_mode(self):
        with patch("metrics.settings") as mock_settings:
            mock_settings.demo_mode = True
            mock_settings.aws_region = "us-east-1"

            import metrics

            with patch.object(metrics.logger, "info") as log_spy:
                await metrics.emit_timer("mission_duration_seconds", 12.5)
                log_spy.assert_called_once()
                assert log_spy.call_args[1]["value"] == 12.5

    @pytest.mark.asyncio
    async def test_emit_gauge_logs_in_demo_mode(self):
        with patch("metrics.settings") as mock_settings:
            mock_settings.demo_mode = True
            mock_settings.aws_region = "us-east-1"

            import metrics

            with patch.object(metrics.logger, "info") as log_spy:
                await metrics.emit_gauge("websocket_connections_active", 5)
                log_spy.assert_called_once()
                assert log_spy.call_args[1]["value"] == 5


class TestMetricsBuffer:
    """Buffer batching logic."""

    @pytest.mark.asyncio
    async def test_buffer_accumulates_below_threshold(self):
        with patch("metrics.settings") as mock_settings:
            mock_settings.demo_mode = False
            mock_settings.aws_region = "us-east-1"

            import metrics

            with patch.object(metrics, "_put_metric_data", new_callable=AsyncMock) as put_spy:
                for _ in range(5):
                    await metrics.emit_counter("test_metric")
                # Below threshold (20) — should NOT have flushed.
                put_spy.assert_not_called()
                assert len(metrics._buffer) == 5

    @pytest.mark.asyncio
    async def test_buffer_flushes_at_threshold(self):
        with patch("metrics.settings") as mock_settings:
            mock_settings.demo_mode = False
            mock_settings.aws_region = "us-east-1"

            import metrics

            with patch.object(metrics, "_put_metric_data", new_callable=AsyncMock) as put_spy:
                for _ in range(20):
                    await metrics.emit_counter("test_metric")
                put_spy.assert_called_once()
                assert len(put_spy.call_args[0][0]) == 20
                assert len(metrics._buffer) == 0

    @pytest.mark.asyncio
    async def test_manual_flush(self):
        with patch("metrics.settings") as mock_settings:
            mock_settings.demo_mode = False
            mock_settings.aws_region = "us-east-1"

            import metrics

            with patch.object(metrics, "_put_metric_data", new_callable=AsyncMock) as put_spy:
                await metrics.emit_counter("a")
                await metrics.emit_counter("b")
                assert len(metrics._buffer) == 2
                await metrics.flush()
                put_spy.assert_called_once()
                assert len(metrics._buffer) == 0


class TestBuildDatum:
    def test_build_datum_with_dimensions(self):
        import metrics

        datum = metrics._build_datum("m", 1.0, "Count", {"k": "v"})
        assert datum["MetricName"] == "m"
        assert datum["Dimensions"] == [{"Name": "k", "Value": "v"}]

    def test_build_datum_without_dimensions(self):
        import metrics

        datum = metrics._build_datum("m", 2.0, "Seconds", None)
        assert "Dimensions" not in datum


# ---------------------------------------------------------------------------
# X-Ray tracing tests
# ---------------------------------------------------------------------------


class TestXRayMiddleware:
    """Verify the middleware creates and closes segments."""

    @pytest.mark.asyncio
    async def test_middleware_creates_segment(self):
        mock_recorder = MagicMock()
        mock_segment = MagicMock()
        mock_recorder.begin_segment.return_value = mock_segment

        with patch("tracing._recorder", mock_recorder):
            from starlette.testclient import TestClient
            from fastapi import FastAPI

            from tracing import XRayMiddleware

            test_app = FastAPI()
            test_app.add_middleware(XRayMiddleware)

            @test_app.get("/test/{mission_id}")
            async def test_route(mission_id: str):
                return {"ok": True}

            client = TestClient(test_app)
            resp = client.get("/test/abc-123")
            assert resp.status_code == 200

            mock_recorder.begin_segment.assert_called()
            mock_recorder.end_segment.assert_called()

    @pytest.mark.asyncio
    async def test_middleware_records_exception(self):
        mock_recorder = MagicMock()
        mock_segment = MagicMock()
        mock_recorder.begin_segment.return_value = mock_segment

        with patch("tracing._recorder", mock_recorder):
            from starlette.testclient import TestClient
            from fastapi import FastAPI

            from tracing import XRayMiddleware

            test_app = FastAPI()
            test_app.add_middleware(XRayMiddleware)

            @test_app.get("/boom")
            async def boom():
                raise RuntimeError("test error")

            client = TestClient(test_app, raise_server_exceptions=False)
            client.get("/boom")

            mock_segment.add_exception.assert_called()
            mock_recorder.end_segment.assert_called()


class TestTraceSubsegment:
    def test_noop_in_demo_mode(self):
        with patch("tracing.settings") as mock_settings:
            mock_settings.demo_mode = True

            from tracing import trace_subsegment

            with trace_subsegment("test") as sub:
                assert sub is None  # no-op

    def test_creates_subsegment_in_prod_mode(self):
        mock_recorder = MagicMock()
        mock_sub = MagicMock()
        mock_recorder.begin_subsegment.return_value = mock_sub

        with (
            patch("tracing.settings") as mock_settings,
            patch("tracing._recorder", mock_recorder),
        ):
            mock_settings.demo_mode = False

            from tracing import trace_subsegment

            with trace_subsegment("fetch", mission_id="m1"):
                pass

            mock_recorder.begin_subsegment.assert_called_once_with("fetch")
            mock_sub.put_annotation.assert_called_once_with("mission_id", "m1")
            mock_recorder.end_subsegment.assert_called_once()
