"""Deterministic distributed-boundary tests; no model or evaluation labels."""

import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import fakeredis
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from agent_platform.app import create_app
from agent_platform.distributed import RedisModelPermits, RedisRateLimiter
from agent_platform.event_transport import EventTransport
from agent_platform.metrics import DurableCollector, event_deltas, install_metrics
from agent_platform.models import PlatformError, TraceEvent, utc_now
from agent_platform.queue_service import QueueTaskService
from agent_platform.runtime import FakeRuntime
from agent_platform.storage import InMemoryTaskStore


def clients():
    server = fakeredis.FakeServer()
    return [fakeredis.FakeRedis(server=server, decode_responses=True) for _ in range(2)]


def event(sequence=1, kind="model.completed", **payload):
    return TraceEvent(
        task_id="task",
        session_id="session",
        sequence=sequence,
        stage_id="solve",
        event_type=kind,
        created_at=utc_now(),
        payload=payload,
    )


def test_global_rate_limiter_and_failure_fencing():
    left, right = clients()
    a, b = RedisRateLimiter(left, "test"), RedisRateLimiter(right, "test")
    a.consume("tasks", "session", 1, 0.001)
    with pytest.raises(PlatformError, match="rate_limit_exceeded"):
        b.consume("tasks", "session", 1, 0.001)
    b.consume("tasks", "other-session", 1, 0.001)
    right.eval = Mock(side_effect=ConnectionError("private credential"))
    with pytest.raises(PlatformError, match="rate_limit_unavailable") as error:
        b.consume("tasks", "session", 1, 0.001)
    assert "private" not in str(error.value)


def test_global_eight_permits_and_release_across_threads():
    left, right = clients()
    permits = [RedisModelPermits(left, "test"), RedisModelPermits(right, "test")]
    entered, leave = threading.Barrier(9), threading.Event()

    def hold(index):
        owner = permits[index % 2]
        assert owner.acquire()
        entered.wait(timeout=5)
        leave.wait(timeout=5)
        owner.release()

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(hold, i) for i in range(8)]
        entered.wait(timeout=5)
        assert left.zcard(permits[0].key) == 8
        assert not permits[0].acquire(timeout=0)
        leave.set()
        for result in futures:
            result.result()
    assert left.zcard(permits[0].key) == 0
    assert permits[1].acquire()
    with pytest.raises(RuntimeError, match="nested"):
        permits[1].acquire()
    permits[1].release()


def test_seven_normal_calls_leave_one_global_slot_for_recovery():
    left, right = clients()
    normal = RedisModelPermits(left, "test", reserve_recovery=True)
    recovery = RedisModelPermits(right, "test")
    # Expired/dead owners are conservatively retained while their calls might live.
    import time

    for index in range(7):
        left.zadd(normal.key, {f"normal-{index}": time.time() + 780})
    assert not normal.acquire(timeout=0)
    assert recovery.acquire()
    assert left.zcard(normal.key) == 8
    recovery.release()


@pytest.mark.parametrize("kwargs", [{"capacity": 0}, {"ttl": 779}, {"renew_seconds": 11}])
def test_invalid_permit_config(kwargs):
    with pytest.raises(ValueError):
        RedisModelPermits(clients()[0], "test", **kwargs)


def test_lost_renewal_and_redis_failure_do_not_fabricate_capacity():
    left, _ = clients()
    permit = RedisModelPermits(left, "test", renew_seconds=0.01)
    assert permit.acquire()
    left.eval = Mock(side_effect=ConnectionError("secret"))
    until = time.monotonic() + 2
    while permit.check_current() and time.monotonic() < until:
        time.sleep(0.005)
    assert not permit.check_current()
    left.zrem = Mock(side_effect=ConnectionError())
    permit.release()
    with pytest.raises(PlatformError, match="model_capacity_unavailable"):
        permit.acquire()


def test_stream_idempotency_gap_rebuild_and_pg_fallback():
    left, _ = clients()
    rows = [event(i, "stage.completed") for i in range(1, 5)]
    store = Mock()
    store.get_task.return_value = SimpleNamespace(event_sequence=4)
    store.events_after.side_effect = lambda session, task, seq, limit=500: rows[seq : seq + limit]
    store.unpublished_events.return_value = rows
    transport = EventTransport(left, store, "test")
    assert transport.publish(rows[-1])
    assert transport.publish(rows[-1])
    assert left.xlen(transport.keys("task")[0]) == 4
    assert transport.events_after("session", "task", 1) == rows[1:]
    assert transport.flush() == 4
    assert store.mark_published.call_count == 4
    left.delete(*transport.keys("task"))
    assert transport.publish(rows[-1])
    left.xrange = Mock(side_effect=ConnectionError())
    assert transport.events_after("session", "task", 0) == rows
    # Authoritative ownership is checked before Redis is accessed.
    store.get_task.side_effect = PlatformError("task_not_found", 404)
    with pytest.raises(PlatformError, match="task_not_found"):
        transport.events_after("foreign", "task", 0)


def test_outbox_is_not_acknowledged_when_redis_publication_fails():
    redis = Mock()
    redis.get.side_effect = ConnectionError()
    store = Mock()
    store.unpublished_events.return_value = [event()]
    with pytest.raises(ConnectionError):
        EventTransport(redis, store).flush()
    store.mark_published.assert_not_called()


def test_corrupt_stream_and_ahead_cursor_fall_back_to_authority():
    redis, _ = clients()
    store = Mock()
    store.get_task.return_value = SimpleNamespace(event_sequence=2)
    store.events_after.return_value = [event()]
    transport = EventTransport(redis, store)
    redis.xadd(transport.keys("task")[0], {"event": "not-json"}, id="1-0")
    assert transport.events_after("session", "task", 0) == store.events_after.return_value
    store.events_after.assert_called_with("session", "task", 0, 500)
    transport.events_after("session", "task", 3)
    store.events_after.assert_called_with("session", "task", 3, 500)


def test_queue_recovery_priority_ids_only_and_transient_failure():
    store, celery, transport = Mock(), Mock(), Mock()
    store.list_interrupted.return_value = [
        SimpleNamespace(
            id="a", session_id="s", runtime_mode="fake", error_code=None, checkpoint={}
        ),
        SimpleNamespace(id="b", session_id="s", runtime_mode="other", error_code=None),
    ]
    store.dispatch_due.return_value = [
        SimpleNamespace(id="c", session_id="s", resume_requested=False),
        SimpleNamespace(id="a", session_id="s", resume_requested=True),
    ]
    service = QueueTaskService(store, FakeRuntime(), celery, transport)
    service.discover_once()
    store.resume.assert_called_once_with("s", "a")
    assert celery.send_task.call_args_list[0].kwargs == {
        "args": ["s", "c"],
        "queue": "reasoning",
        "retry": False,
    }
    assert celery.send_task.call_args_list[1].kwargs["queue"] == "recovery"
    celery.send_task.side_effect = ConnectionError()
    service.discover_once()
    assert service.operational_health()["reasons"] == ["dispatch_failed"]
    assert transport.flush.call_count == 2


def test_queue_service_start_stop_and_incompatible_checkpoint():
    store, celery, transport = Mock(), Mock(), Mock()
    store.list_interrupted.return_value = [
        SimpleNamespace(id="a", session_id="s", runtime_mode="fake", error_code=None, checkpoint={})
    ]
    store.dispatch_due.return_value = []
    runtime = FakeRuntime()
    runtime.checkpoint_compatible = lambda value: False
    service = QueueTaskService(store, runtime, celery, transport, poll_seconds=0.01)
    service.discover_once()
    store.reject_checkpoint.assert_called_once_with("s", "a")

    async def lifecycle():
        await service.start()
        await asyncio.sleep(0.03)
        await service.stop()
        assert not service.accepting and service.discovery is None

    asyncio.run(lifecycle())


def test_metrics_finite_labels_missing_tokens_and_http_sse():
    deltas = list(
        event_deltas(event(usage={"total_tokens": 3, "prompt_tokens": True}, duration_ms=12))
    )
    assert ("maths_model_tokens_total", '["total_tokens"]', 3.0) in deltas
    assert not any("prompt_tokens" in labels for _, labels, _ in deltas)
    assert any(name == "maths_token_usage_missing_total" for name, _, _ in event_deltas(event()))
    for name, labels, value in event_deltas(event(name="arbitrary", latency_ms=float("nan"))):
        assert "arbitrary" not in labels
    store = InMemoryTaskStore()
    app = create_app(store=store, runtime=FakeRuntime(0.001), rate_limits=False)
    install_metrics(app, store)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        task = client.post(f"/v1/sessions/{session}/tasks", json={"problem": "fixture"}).json()
        assert client.get(task["events_url"]).status_code == 200
        metrics = client.get("/metrics").text
        assert "maths_sse_connection_first_frame_seconds_count 1.0" in metrics
        assert task["id"] not in metrics and session not in metrics
        assert 'route="/v1/sessions/{session_id}/tasks"' in metrics


def test_durable_collector_exposes_committed_not_process_local_counters():
    store = Mock()
    store.metric_rows.return_value = [
        {"name": name, "labels": labels, "value": value}
        for name, labels, value in event_deltas(event(usage={"total_tokens": 4}, duration_ms=50))
    ]
    store.status_counts.return_value = {"queued": 2}
    from prometheus_client import CollectorRegistry, generate_latest

    registry = CollectorRegistry()
    registry.register(DurableCollector(store))
    output = generate_latest(registry).decode()
    assert 'maths_model_tokens_total{kind="total_tokens"} 4.0' in output
    assert 'maths_tasks{status="queued"} 2.0' in output
    assert "maths_operation_seconds_bucket" in output
    assert "session" not in json.dumps([metric.name for metric in registry.collect()])
