import concurrent.futures
import json

import pytest

from agent_platform.models import PlatformError, TaskStatus
from agent_platform.runtime import FakeRuntime, RuntimeContext
from agent_platform.safety import sanitize, sanitize_text, validate_metadata
from agent_platform.storage import InMemoryTaskStore


def submit(store, session, problem="problem", key=None):
    return store.create_task(session.id, problem, {}, "fake", key)[0]


def test_atomic_idempotency_and_capacity_under_concurrent_admission():
    store = InMemoryTaskStore(max_queued=1)
    session = store.create_session(100)
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: store.create_task(session.id, "same", {}, "fake", "key"), range(32)))
    assert len({task.id for task, _ in results}) == 1
    assert sum(created for _, created in results) == 1
    assert len(store.list_queued()) == 1
    with pytest.raises(PlatformError, match="idempotency_conflict"):
        submit(store, session, "different", "key")
    with pytest.raises(PlatformError, match="queue_capacity_exceeded"):
        submit(store, session, "another")


def test_atomic_capacity_for_different_concurrent_submissions():
    store = InMemoryTaskStore(max_queued=3)
    session = store.create_session(0)

    def attempt(index):
        try:
            return submit(store, session, str(index))
        except PlatformError:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(attempt, range(32)))
    assert sum(result is not None for result in results) == 3


@pytest.mark.parametrize("pair", range(100))
def test_paired_session_message_checkpoint_filter_and_trace_isolation(pair):
    store = InMemoryTaskStore()
    a, b = store.create_session(1000), store.create_session(1000)
    secret = f"session_A_private_{pair}"
    first = submit(store, a, secret)
    running = store.start(a.id, first.id, 1200)
    store.progress(a.id, first.id, running.generation, "retrieve", True,
                   {"filter": {"session_id": a.id}, "private": secret})
    store.finish(a.id, first.id, running.generation, TaskStatus.SUCCEEDED, secret)
    task_a, task_b = submit(store, a), submit(store, b)
    assert secret in " ".join(message.content for message in task_a.memory)
    assert not task_b.memory
    assert task_b.checkpoint is None
    assert secret not in json.dumps([event.model_dump(mode="json") for event in task_b.events])
    for method in [store.get_task, store.cancel, store.resume]:
        with pytest.raises(PlatformError, match="task_not_found"):
            method(b.id, first.id)
    with pytest.raises(PlatformError, match="task_not_found"):
        store.events_after(b.id, first.id, 0)


def test_memory_cutoff_and_budget_are_stable_snapshots():
    store = InMemoryTaskStore()
    session = store.create_session(8)
    first = submit(store, session, "previous")
    second = submit(store, session, "current")
    third = submit(store, session, "future")
    assert [m.content for m in first.memory] == []
    assert [m.content for m in second.memory] == ["previous"]
    assert [m.content for m in third.memory] == ["current"]
    assert [m.content for m in second.memory] == ["previous"]
    retrieved = store.get_session(session.id)
    retrieved.messages.clear()
    assert store.get_session(session.id).messages


def test_start_cancel_finish_resume_and_fencing():
    store = InMemoryTaskStore()
    session = store.create_session(100)
    task = submit(store, session)
    original = store.start(session.id, task.id, 1200)
    assert store.start(session.id, task.id, 1200) is None
    with pytest.raises(PlatformError, match="task_not_interrupted"):
        store.resume(session.id, task.id)
    store.progress(session.id, task.id, original.generation, "plan", True, {"completed_stage": 2})
    interrupted = store.finish(session.id, task.id, original.generation,
                               TaskStatus.INTERRUPTED, error_code="interrupted")
    assert interrupted.finished_at is None
    resumed, created = store.resume(session.id, task.id)
    assert created and resumed.status == TaskStatus.QUEUED
    assert not store.resume(session.id, task.id)[1]
    newer = store.start(session.id, task.id, 1200)
    assert newer.generation == original.generation + 1
    assert newer.started_at == original.started_at
    assert newer.deadline_at == original.deadline_at
    assert not store.resume(session.id, task.id)[1]
    with pytest.raises(PlatformError, match="stale_execution"):
        store.progress(session.id, task.id, original.generation, "solve", False, None)
    assert store.finish(session.id, task.id, original.generation, TaskStatus.SUCCEEDED, "stale").status == TaskStatus.RUNNING
    assert store.cancel(session.id, task.id).status == TaskStatus.CANCELLING
    assert store.cancel(session.id, task.id).status == TaskStatus.CANCELLING
    with pytest.raises(PlatformError, match="stale_execution"):
        store.progress(session.id, task.id, newer.generation, "solve", False, None)
    final = store.finish(session.id, task.id, newer.generation, TaskStatus.SUCCEEDED, "must not win")
    assert final.status == TaskStatus.CANCELLED and final.final_response is None
    assert store.cancel(session.id, task.id).status == TaskStatus.CANCELLED
    assert store.finish(session.id, task.id, newer.generation, TaskStatus.FAILED).status == TaskStatus.CANCELLED
    with pytest.raises(PlatformError, match="task_not_interrupted"):
        store.resume(session.id, task.id)


def test_cancel_queued_or_interrupted_and_completed_conflict():
    store = InMemoryTaskStore()
    session = store.create_session(0)
    queued = submit(store, session)
    assert store.cancel(session.id, queued.id).status == TaskStatus.CANCELLED
    interrupted = submit(store, session)
    running = store.start(session.id, interrupted.id, 1200)
    store.finish(session.id, interrupted.id, running.generation, TaskStatus.INTERRUPTED)
    assert store.cancel(session.id, interrupted.id).status == TaskStatus.CANCELLED
    complete = submit(store, session)
    running = store.start(session.id, complete.id, 1200)
    store.progress(session.id, complete.id, running.generation, "solve", True, None)
    store.finish(session.id, complete.id, running.generation, TaskStatus.SUCCEEDED, "done")
    with pytest.raises(PlatformError, match="task_already_terminal"):
        store.cancel(session.id, complete.id)
    with pytest.raises(PlatformError, match="cursor_ahead"):
        store.events_after(session.id, complete.id, 100)
    assert store.events_after(session.id, complete.id, len(store.get_task(session.id, complete.id).events)) == []
    with pytest.raises(PlatformError, match="session_not_found"):
        store.get_session("missing")


def test_resume_obeys_capacity():
    store = InMemoryTaskStore(max_queued=1)
    session = store.create_session(0)
    task = submit(store, session)
    running = store.start(session.id, task.id, 1200)
    store.finish(session.id, task.id, running.generation, TaskStatus.INTERRUPTED)
    submit(store, session)
    with pytest.raises(PlatformError, match="queue_capacity_exceeded"):
        store.resume(session.id, task.id)


@pytest.mark.parametrize("metadata,code", [
    ({"answer": "hidden"}, "reserved_metadata_field"),
    ({"nested": [{"API-Key": "hidden"}]}, "reserved_metadata_field"),
    ({"text": "x" * 8000}, "metadata_too_large"),
    ({"score": float("nan")}, "invalid_metadata"),
])
def test_metadata_rejection(metadata, code):
    with pytest.raises(PlatformError, match=code):
        validate_metadata(metadata)


def test_sanitizer_and_nested_metadata():
    secret = "sk-canarycredential123456789"
    value = {"prompt": "private", "items": [secret, "Bearer abc123", "password=hunter2",
             "postgresql://user:pass@server", r"C:\private\local.txt"], "n": 2, "ok": True,
             "unsupported": object(), "bad": float("inf")}
    text = json.dumps(sanitize(value))
    for forbidden in [secret, "private", "abc123", "hunter2", "user:pass", "local.txt"]:
        assert forbidden not in text
    assert "[redacted]" in text and "[unsupported value]" in text
    assert sanitize(None) is None
    assert sanitize({"ok": [[[[[[[[[["x"]]]]]]]]]]}) is not None
    deep = {}
    for _ in range(10):
        deep = {"nested": deep}
    with pytest.raises(PlatformError, match="metadata_too_deep"):
        validate_metadata(deep)
    assert validate_metadata(None) == {}
    assert validate_metadata({"domain": "algebra", "idx": 3}) == {"domain": "algebra", "idx": 3}
    assert sanitize_text("f(x)=x+1") == "f(x)=x+1"


def test_runtime_context_rejects_unknown_stage_and_retains_sanitized_candidate():
    progress = []
    context = RuntimeContext("task", "session", "problem", {}, (), None,
                             lambda *args: progress.append(args))
    with pytest.raises(ValueError, match="invalid_stage"):
        context.progress("untrusted_stage")
    context.progress("plan", completed=True, checkpoint={"completed_stage": 2})
    context.save_response("  ")
    assert context.saved_response is None
    context.save_response("answer sk-canarycredential123456789")
    assert "sk-" not in context.saved_response
    assert len(progress) == 1
