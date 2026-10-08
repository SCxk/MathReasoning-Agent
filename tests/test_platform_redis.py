import concurrent.futures
import asyncio
import json
import time
from unittest.mock import patch

import pytest

fakeredis = pytest.importorskip("fakeredis")

from agent_platform.models import PlatformError, TaskStatus
from agent_platform.redis_store import RedisTaskStore
from agent_platform.runtime import FakeRuntime
from agent_platform.service import TaskService


def store_pair(**kwargs):
    server = fakeredis.FakeServer()
    clients = [fakeredis.FakeRedis(server=server, decode_responses=True) for _ in range(2)]
    return [RedisTaskStore(client, require_aof=False, **kwargs) for client in clients]


def new_task(store):
    session = store.create_session(100)
    task, _ = store.create_task(session.id, "generic problem", {}, "fake", "key")
    return session.id, task.id


def test_question_task_lookup_is_readonly_scoped_and_memory_is_empty():
    first, second = store_pair()
    session, previous = new_task(first)
    value, _ = first.create_task(session, "question fixture", {"_question_source": {"batch_id": "fixture"}}, "fake", "question-key")
    assert value.memory == ()
    assert second.lookup_submission(session, "question-key").id == value.id
    assert second.lookup_submission(session, "missing") is None
    foreign = first.create_session(100).id
    assert second.lookup_submission(foreign, "question-key") is None
    assert len(second.list_tasks(session, 20)[0]) == 2
    assert first.get_task(session, previous).status == TaskStatus.QUEUED


def test_reopen_persists_sessions_checkpoints_events_and_idempotency():
    first, second = store_pair()
    session, task_id = new_task(first)
    task = first.start(session, task_id, 1200)
    first.progress(session, task_id, task.generation, "solve", True, {"next_stage": "tool", "candidate": "accepted"})
    first.finish(session, task_id, task.generation, TaskStatus.INTERRUPTED)
    restored = second.get_task(session, task_id)
    assert restored.checkpoint["candidate"] == "accepted"
    assert second.get_session(session).messages[0].task_id == task_id
    duplicate, created = second.create_task(session, "generic problem", {}, "fake", "key")
    assert duplicate.id == task_id and not created
    second.resume(session, task_id)
    restarted = second.start(session, task_id, 1200)
    assert restarted.deadline_at == task.deadline_at
    first.finish(session, task_id, task.generation, TaskStatus.SUCCEEDED, "stale")
    second.finish(session, task_id, restarted.generation, TaskStatus.SUCCEEDED, "accepted")
    events = second.events_after(session, task_id, 0)
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert events[-1].payload["final_response"] == "accepted"
    assert second.get_session(session).messages[-1].content == "accepted"


def test_new_task_validation_is_atomic_and_skipped_for_accepted_retry():
    first, second = store_pair()
    session, identifier = new_task(first)
    def reject():
        raise PlatformError("document_not_ready", 409)
    duplicate, created = second.create_task(session, "generic problem", {}, "fake", "key", reject)
    assert duplicate.id == identifier and not created
    with pytest.raises(PlatformError, match="document_not_ready"):
        second.create_task(session, "new problem", {}, "fake", "new", reject)
    assert len(second.get_session(session).messages) == 1
    assert second.list_sessions(10)["items"][0]["task_count"] == 1
    assert second.client.get(second.key("idem:new")) is None


def test_expired_lease_recovery_and_late_writes_are_fenced():
    first, second = store_pair(lease_seconds=.05)
    session, task_id = new_task(first)
    old = first.start(session, task_id, 1200)
    first.progress(session, task_id, old.generation, "plan", True, {"completed": "plan"})
    time.sleep(.07)
    with pytest.raises(PlatformError, match="stale_execution"):
        first.progress(session, task_id, old.generation, "solve", False, None)
    second.recover_expired()
    assert second.list_interrupted()[0].id == task_id
    second.resume(session, task_id)
    current = second.start(session, task_id, 1200)
    assert current.generation > old.generation
    with pytest.raises(PlatformError, match="stale_execution"):
        first.record(session, task_id, old.generation, "solve", "model.completed", {})
    second.renew(session, task_id, current.generation)
    assert second.get_task(session, task_id).lease_until >= current.lease_until


def test_cancelled_interrupted_task_is_not_recoverable():
    first, second = store_pair(lease_seconds=.03)
    session, task_id = new_task(first)
    task = first.start(session, task_id, 1200)
    first.cancel(session, task_id)
    time.sleep(.04)
    second.recover_expired()
    assert second.get_task(session, task_id).status == TaskStatus.CANCELLED
    assert second.list_interrupted() == []


def test_queue_and_global_execution_limits_duplicate_creation():
    first, second = store_pair(max_queued=2, max_running=1)
    session, task_id = new_task(first)
    with concurrent.futures.ThreadPoolExecutor(8) as executor:
        duplicates = list(executor.map(lambda _: second.create_task(session, "generic problem", {}, "fake", "key"), range(12)))
    assert all(task.id == task_id and not created for task, created in duplicates)
    other, _ = second.create_task(session, "another problem", {}, "fake", None)
    with pytest.raises(PlatformError, match="queue_capacity_exceeded"):
        first.create_task(session, "extra problem", {}, "fake", None)
    started = first.start(session, task_id, 1200)
    assert second.start(session, other.id, 1200) is None
    first.finish(session, task_id, started.generation, TaskStatus.SUCCEEDED, "done")
    assert second.start(session, other.id, 1200)


@pytest.mark.parametrize("index", range(100))
def test_redis_isolation(index):
    first, second = store_pair()
    session, task_id = new_task(first)
    foreign = second.create_session(100)
    with pytest.raises(PlatformError, match="task_not_found"):
        second.get_task(foreign.id, task_id)
    with pytest.raises(PlatformError, match="task_not_found"):
        second.events_after(foreign.id, task_id, 0)
    assert second.get_session(foreign.id).messages == []


def test_checkpoint_and_trace_secrets_sanitized():
    first, second = store_pair()
    session, task_id = new_task(first)
    task = first.start(session, task_id, 1200)
    value = "password=private"
    first.progress(session, task_id, task.generation, "solve", True, {"candidate": value, "api_key": "private"})
    first.record(session, task_id, task.generation, "solve", "model.completed", {"raw_response": "private", "note": value})
    assert "private" not in json.dumps(second.get_task(session, task_id).checkpoint)
    assert "private" not in json.dumps([event.model_dump(mode="json") for event in second.events_after(session, task_id, 0)])


def test_outage_and_aof_configuration_fail_closed():
    first, _ = store_pair()
    from redis.exceptions import ConnectionError
    with patch.object(first.client, "ping", side_effect=ConnectionError()), \
         pytest.raises(PlatformError, match="storage_unavailable"):
        first.ready()
    client = fakeredis.FakeRedis(decode_responses=True)
    with pytest.raises(PlatformError):
        RedisTaskStore(client)
    with pytest.raises(ValueError):
        RedisTaskStore(client, namespace="bad/path", require_aof=False)
    with pytest.raises(ValueError, match="redis_decode_responses_required"):
        RedisTaskStore(fakeredis.FakeRedis(), require_aof=False)


def test_aof_health_contract_and_invalid_limits():
    first, _ = store_pair()
    with patch.object(first.client, "info", return_value={"aof_enabled": 1, "aof_last_write_status": "ok"}), \
         patch.object(first.client, "config_get", return_value={"appendfsync": "always"}):
        durable = RedisTaskStore(first.client)
        assert durable.restart_durable and durable.ready()
        assert durable.create_session(0).id
    with patch.object(first.client, "info", return_value={"aof_enabled": 1, "aof_last_write_status": "ok"}), \
         patch.object(first.client, "config_get", return_value={"appendfsync": "everysec"}), \
         pytest.raises(PlatformError, match="redis_aof_always_required"):
        RedisTaskStore(first.client)
    with pytest.raises(ValueError):
        RedisTaskStore(first.client, max_queued=0, require_aof=False)


def test_conflicts_missing_records_and_cursor():
    first, second = store_pair()
    session, task_id = new_task(first)
    assert second.queue_position(task_id) == 1
    assert second.list_queued()[0].id == task_id
    with pytest.raises(PlatformError, match="idempotency_conflict"):
        second.create_task(session, "different", {}, "fake", "key")
    with pytest.raises(PlatformError, match="session_not_found"):
        second.get_session("missing")
    with pytest.raises(PlatformError, match="session_not_found"):
        second.create_task("missing", "input", {}, "fake", None)
    with pytest.raises(PlatformError, match="task_not_found"):
        second.get_task(session, "missing")
    with pytest.raises(PlatformError, match="task_not_found"):
        second.cancel(session, "missing")
    with pytest.raises(PlatformError, match="cursor_ahead"):
        second.events_after(session, task_id, 99)
    first.cancel(session, task_id)
    assert second.queue_position(task_id) is None and second.list_queued() == []
    assert second.start(session, task_id, 1200) is None
    with pytest.raises(PlatformError, match="stale_execution"):
        second.renew(session, task_id, 0)


def test_transaction_view_and_missing_index_records():
    from agent_platform.redis_store import _TransactionView
    view = _TransactionView([], 1)
    assert view.queue_position("missing") is None
    first, _ = store_pair()
    session, task_id = new_task(first)
    first.client.delete(first.key(f"task:{task_id}"))
    first.client.zadd(first.key("active"), {task_id: 0})
    first.recover_expired()
    with pytest.raises(PlatformError, match="task_not_found"):
        first.create_task(session, "generic problem", {}, "fake", "key")


@pytest.mark.parametrize("method", ["_transaction", "_get", "_list", "queue_position", "recover_expired", "events_after"])
def test_storage_operation_outages(method):
    from redis.exceptions import ConnectionError
    first, _ = store_pair()
    session, task_id = new_task(first)
    operation = {"_transaction": "pipeline", "_get": "get", "_list": "zrange",
                 "queue_position": "zrank", "recover_expired": "zrangebyscore", "events_after": "lrange"}[method]
    arguments = {"_transaction": ("create_session", 0), "_get": ("missing",), "_list": ("queued",),
                 "queue_position": (task_id,), "recover_expired": (), "events_after": (session, task_id, 0)}[method]
    with patch.object(first.client, operation, side_effect=ConnectionError()), \
         pytest.raises(PlatformError, match="storage_unavailable"):
        getattr(first, method)(*arguments)


def test_transaction_contention_retry_budget():
    from redis.exceptions import WatchError
    first, _ = store_pair()
    with patch.object(first.client, "pipeline", side_effect=WatchError()), \
         pytest.raises(PlatformError, match="storage_busy"):
        first.create_session(0)


def test_interrupted_operation_has_one_outcome_and_started_call_count_is_durable():
    first, second = store_pair(lease_seconds=.03)
    session, task_id = new_task(first)
    task = first.start(session, task_id, 1200)
    first.record(session, task_id, task.generation, "solve", "model.started", {
        "call_type": "solver", "operation_id": "operation",
    })
    time.sleep(.04)
    second.recover_expired()
    assert second.get_task(session, task_id).model_calls == {"solver": 1}
    assert second.get_task(session, task_id).active_operations == {}
    events = second.events_after(session, task_id, 0)
    outcomes = [event for event in events if event.payload.get("operation_id") == "operation"]
    assert [event.event_type for event in outcomes] == ["model.started", "model.interrupted"]


def test_service_recovery_renewal_and_storage_failure_retry():
    async def check():
        first, second = store_pair(lease_seconds=.09)
        session, task_id = new_task(first)
        old = first.start(session, task_id, 1200)
        first.progress(session, task_id, old.generation, "plan", True, {"completed_stage": 2})
        time.sleep(.1)
        service = TaskService(second, FakeRuntime(.035), recovery_poll_seconds=.01)
        original = second.recover_expired
        calls = 0
        def fail_once():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("transient")
            original()
        with patch.object(second, "recover_expired", side_effect=fail_once):
            await service.start()
            for _ in range(100):
                await asyncio.sleep(.01)
                task = second.get_task(session, task_id)
                if task.status == TaskStatus.SUCCEEDED:
                    break
            await service.stop()
        assert task.status == TaskStatus.SUCCEEDED
        assert task.generation > old.generation
        assert calls > 2
        assert task.checkpoint["completed_stage"] == 7
        assert not service._workers and service._reconciler is None
    asyncio.run(check())


def test_service_lease_failure_cancels_execution_and_resumes_it():
    async def check():
        first, _ = store_pair()
        service = TaskService(first, FakeRuntime(.02), recovery_poll_seconds=.01)
        await service.start()
        session = first.create_session(0)
        observed = asyncio.Event()
        def renewal_failure(*args):
            observed.set()
            raise PlatformError("storage_unavailable", 503)
        with patch.object(first, "lease_seconds", .09), \
             patch.object(first, "renew", side_effect=renewal_failure):
            task = service.submit(session.id, "input", {}, None)
            await asyncio.wait_for(observed.wait(), 1)
        for _ in range(100):
            await asyncio.sleep(.01)
            final = first.get_task(session.id, task.id)
            if final.status == TaskStatus.SUCCEEDED:
                break
        await service.stop()
        assert final.status == TaskStatus.SUCCEEDED
        assert final.generation >= 2
    asyncio.run(check())


def test_service_outage_does_not_lose_worker_or_delivery():
    async def check():
        first, _ = store_pair()
        service = TaskService(first, FakeRuntime(0), recovery_poll_seconds=.01)
        original = first.start
        count = 0
        def fail_once(*args):
            nonlocal count
            count += 1
            if count == 1:
                raise PlatformError("storage_unavailable", 503)
            return original(*args)
        await service.start()
        session = first.create_session(0)
        with patch.object(first, "start", side_effect=fail_once):
            task = service.submit(session.id, "input", {}, None)
            for _ in range(100):
                await asyncio.sleep(.01)
                final = first.get_task(session.id, task.id)
                if final.status == TaskStatus.SUCCEEDED:
                    break
        await service.stop()
        assert final.status == TaskStatus.SUCCEEDED and count >= 2
    asyncio.run(check())
