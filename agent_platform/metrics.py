"""Bounded-cardinality metrics; durable event counters commit with PostgreSQL events."""

import json
import asyncio
import math
import time
from collections.abc import Iterable
from datetime import datetime, timezone

from prometheus_client import CollectorRegistry, Histogram, generate_latest
from prometheus_client.core import Metric, GaugeMetricFamily
from prometheus_client.registry import Collector
from starlette.responses import Response
from agent_platform.models import PlatformError


STAGES = {"system", "profile", "retrieve", "plan", "solve", "tool", "verify", "repair", "finalize"}
TOOLS = {"strategy_search", "document_search", "math_verify", "sympy_calculate"}
BUCKETS = (0.05, 0.1, 0.3, 1.0, 5.0, 15.0, 30.0, 60.0, 300.0, 1200.0, float("inf"))


def histogram_deltas(base, seconds, labels=None):
    labels = labels or []
    yield base + "_sum", json.dumps(labels), seconds
    yield base + "_count", json.dumps(labels), 1.0
    for bound in BUCKETS:
        if seconds <= bound:
            yield (
                base + "_bucket",
                json.dumps(labels + ["+Inf" if math.isinf(bound) else str(bound)]),
                1.0,
            )


def event_deltas(event):
    stage = event.stage_id if event.stage_id in STAGES else "other"
    kind = event.event_type
    family = (
        kind.split(".")[0]
        if kind.split(".")[0]
        in {"task", "stage", "model", "tool", "retrieval", "verification", "checkpoint"}
        else "other"
    )
    yield "maths_events_total", json.dumps([stage, family]), 1.0
    if kind.startswith("task."):
        status = kind.split(".")[-1]
        if status in {
            "accepted",
            "running",
            "succeeded",
            "failed",
            "cancelled",
            "interrupted",
            "resumed",
        }:
            yield "maths_task_transitions_total", json.dumps([status]), 1.0
    if kind == "model.completed":
        usage = event.payload.get("usage", {})
        if isinstance(usage, dict):
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = usage.get(key)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    yield "maths_model_tokens_total", json.dumps([key]), float(value)
        total = usage.get("total_tokens") if isinstance(usage, dict) else None
        if not isinstance(total, int) or isinstance(total, bool) or total < 0:
            yield "maths_token_usage_missing_total", "[]", 1.0
    if kind in {"tool.completed", "tool.failed"}:
        name = event.payload.get("name")
        name = name if name in TOOLS else "other"
        yield (
            "maths_tool_outcomes_total",
            json.dumps([name, "success" if kind.endswith("completed") else "failure"]),
            1.0,
        )
    if kind == "stage.completed" and stage == "repair":
        yield "maths_repair_stages_total", "[]", 1.0
    if kind == "task.failed" and event.payload.get("error_code") == "task_deadline_exceeded":
        yield "maths_timeouts_total", "[]", 1.0
    milliseconds = (
        event.payload.get("duration_ms")
        if kind in {"model.completed", "stage.completed"}
        else event.payload.get("latency_ms")
        if kind in {"tool.completed", "tool.failed"}
        else None
    )
    if isinstance(milliseconds, (int, float)) and math.isfinite(milliseconds) and milliseconds >= 0:
        base = "maths_operation_seconds"
        labels = [stage, family]
        seconds = milliseconds / 1000
        yield base + "_sum", json.dumps(labels), seconds
        yield base + "_count", json.dumps(labels), 1.0
        for bound in BUCKETS:
            if seconds <= bound:
                yield (
                    base + "_bucket",
                    json.dumps(labels + ["+Inf" if math.isinf(bound) else str(bound)]),
                    1.0,
                )


class DurableCollector(Collector):
    def __init__(self, store):
        self.store = store

    def collect(self) -> Iterable[Metric]:
        counters = {
            "maths_events_total": ["stage", "family"],
            "maths_task_transitions_total": ["status"],
            "maths_model_tokens_total": ["kind"],
            "maths_token_usage_missing_total": [],
            "maths_tool_outcomes_total": ["name", "outcome"],
            "maths_repair_stages_total": [],
            "maths_timeouts_total": [],
            "maths_recovered_outcomes_total": ["outcome"],
        }
        metrics: dict[str, Metric] = {}
        for row in self.store.metric_rows():
            name, values, value = row["name"], json.loads(row["labels"]), row["value"]
            if name in counters:
                metric = metrics.setdefault(
                    name,
                    Metric(name.removesuffix("_total"), "Durable committed events.", "counter"),
                )
                metric.add_sample(name, dict(zip(counters[name], values, strict=True)), value)
            elif any(
                name.startswith(base + "_")
                for base in (
                    "maths_operation_seconds",
                    "maths_task_seconds",
                    "maths_task_first_status_seconds",
                    "maths_lease_recovery_seconds",
                )
            ):
                base = name.rsplit("_", 1)[0]
                metric = metrics.setdefault(
                    base,
                    Metric(base, "Committed latency observation.", "histogram"),
                )
                names = ["stage", "family"] if base == "maths_operation_seconds" else []
                labels = dict(
                    zip(
                        names + (["le"] if name.endswith("_bucket") else []),
                        values,
                        strict=True,
                    )
                )
                metric.add_sample(name, labels, value)
        yield from metrics.values()
        counts = GaugeMetricFamily("maths_tasks", "Authoritative task states.", labels=["status"])
        for status, value in self.store.status_counts().items():
            counts.add_metric([status], value)
        yield counts


def install_metrics(app, store, *, operations=None):
    registry = CollectorRegistry()
    if hasattr(store, "metric_rows"):
        registry.register(DurableCollector(store))
    if operations is not None:
        registry.register(operations)
    latency = Histogram(
        "maths_http_request_seconds",
        "API response latency.",
        ["method", "route"],
        buckets=(0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 3.0, 10.0),
        registry=registry,
    )
    first = Histogram(
        "maths_sse_connection_first_frame_seconds",
        "First frame after SSE connection, not task acceptance.",
        buckets=(0.01, 0.05, 0.1, 0.3, 1.0, 3.0, 15.0),
        registry=registry,
    )
    gap = Histogram(
        "maths_sse_frame_gap_seconds",
        "Gap between SSE frames/heartbeats.",
        buckets=(0.1, 1.0, 5.0, 10.0, 15.0, 20.0, 30.0),
        registry=registry,
    )

    class ObserveHTTP:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                return await self.app(scope, receive, send)
            started, last, is_stream = time.monotonic(), None, False

            async def observed(message):
                nonlocal last, is_stream
                accepted = None
                if message["type"] == "http.response.start":
                    route = getattr(scope.get("route"), "path", "unmatched")
                    is_stream = route.endswith("/events") and message["status"] == 200
                    if route != "/metrics":
                        method = (
                            scope["method"]
                            if scope["method"]
                            in {"GET", "POST", "HEAD", "OPTIONS", "PUT", "DELETE", "PATCH"}
                            else "OTHER"
                        )
                        latency.labels(method, route).observe(time.monotonic() - started)
                if is_stream and message["type"] == "http.response.body" and message.get("body"):
                    now = time.monotonic()
                    if last is None:
                        first.observe(now - started)
                    else:
                        gap.observe(now - last)
                    last = now
                    if hasattr(store, "observe_first_status"):
                        for line in message["body"].decode("utf8").splitlines():
                            if line.startswith("data: "):
                                event = json.loads(line[6:])
                                if event.get("event_type") == "task.accepted":
                                    accepted = event
                await send(message)
                if accepted:
                    seconds = (
                        datetime.now(timezone.utc) - datetime.fromisoformat(accepted["created_at"])
                    ).total_seconds()
                    try:
                        await asyncio.to_thread(
                            store.observe_first_status,
                            accepted["session_id"],
                            accepted["task_id"],
                            max(0, seconds),
                        )
                    except PlatformError:
                        pass  # Instrumentation must not terminate a replayable stream.

            await self.app(scope, receive, observed)

    app.add_middleware(ObserveHTTP)

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return Response(
            generate_latest(registry), media_type="text/plain; version=0.0.4; charset=utf-8"
        )

    app.state.metrics = registry
