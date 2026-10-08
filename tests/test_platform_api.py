import asyncio
import json
import time

import pytest

pytest.importorskip("fastapi", reason="install requirements-platform.txt for HTTP platform tests")
pytest.importorskip("httpx", reason="install requirements-platform.txt for HTTP platform tests")

from fastapi.testclient import TestClient
from starlette.requests import Request

from agent_platform.app import LocalRateLimiter, StreamBudget, create_app
from agent_platform.models import PlatformError, TaskStatus
from agent_platform.runtime import FakeRuntime, RuntimeResult
from agent_platform.service import TaskService
from agent_platform.storage import InMemoryTaskStore


def new_session(client):
    response = client.post("/v1/sessions", json={})
    assert response.status_code == 201
    return response.json()["id"]


def create_task(client, session, **kwargs):
    response = client.post(f"/v1/sessions/{session}/tasks", json={"problem": "test input"}, **kwargs)
    assert response.status_code == 202, response.text
    return response.json()


def wait_for_status(client, task, statuses={"succeeded", "failed", "cancelled"}):
    until = time.monotonic() + 3
    while time.monotonic() < until:
        result = client.get(task["status_url"])
        assert result.status_code == 200
        if result.json()["status"] in statuses:
            return result.json()
        time.sleep(.005)
    pytest.fail("task failed to reach expected status")


def decode_events(text):
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def test_end_to_end_stream_trace_pagination_and_replay():
    with TestClient(create_app(runtime=FakeRuntime(.002), rate_limits=False)) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").json()["restart_durable"] is False
        assert client.get("/", follow_redirects=False).headers["location"] == "/trace-viewer"
        assert "MathReasoning-Agent" in client.get("/trace-viewer").text
        assert client.get("/openapi.json").status_code == 200
        session = new_session(client)
        task = create_task(client, session)
        assert task["status"] == "queued" and task["deadline_at"] is None
        assert task["runtime_mode"] == "fake"
        stream = client.get(task["events_url"])
        assert stream.headers["content-type"].startswith("text/event-stream")
        events = decode_events(stream.text)
        assert events[0]["event_type"] == "task.accepted"
        assert events[-1]["event_type"] == "task.succeeded"
        assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
        final = wait_for_status(client, task)
        assert final["final_response"] and final["checkpoint_available"]
        assert "problem" not in final and "metadata" not in final
        first_page = client.get(task["trace_url"], params={"limit": 3}).json()
        second_page = client.get(task["trace_url"], params={"after_sequence": first_page["next_sequence"]}).json()
        assert first_page["events"] + second_page["events"] == events
        replay = decode_events(client.get(task["events_url"], headers={"Last-Event-ID": "3"}).text)
        assert replay == events[3:]
        assert decode_events(client.get(task["events_url"], params={"after": len(events)}).text) == []
        assert client.get(task["events_url"], params={"after": len(events) + 1}).status_code == 409
        assert client.get(task["events_url"], headers={"Last-Event-ID": "bad"}).status_code == 400
        assert client.get(task["events_url"], headers={"Last-Event-ID": "-1"}).status_code == 400
        assert client.get(task["events_url"], params={"after": -1}).status_code == 400
        assert client.get(task["trace_url"], params={"limit": 501}).status_code == 400
        assert client.post(task["status_url"] + "/cancel", json={}).status_code == 409
        assert client.post(task["status_url"] + "/resume").status_code == 409


def test_sse_heartbeats_while_waiting():
    # A task pinned in running state cannot finish before the stream opens.
    # Wall-clock FakeRuntime delays made this test flaky under suite load.
    from unittest.mock import AsyncMock, Mock
    store = InMemoryTaskStore()
    session = store.create_session(0)
    task, _ = store.create_task(session.id, "input", {}, "fake", None)
    store.start(session.id, task.id, 1200)
    app = create_app(store=store, heartbeat_seconds=.005, poll_seconds=.001, rate_limits=False)
    endpoint = next(route.endpoint for route in app.routes if getattr(route, "path", "").endswith("/events"))
    async def run():
        response = await endpoint(Mock(is_disconnected=AsyncMock(return_value=False)),
                                  session.id, task.id, after=0, last_event_id=None)
        frames = []
        try:
            async with asyncio.timeout(1):
                async for frame in response.body_iterator:
                    frames.append(frame)
                    if ": heartbeat" in frame:
                        break
        finally:
            await response.body_iterator.aclose()
        return "".join(frames)
    text = asyncio.run(run())
    assert ": heartbeat" in text
    assert all("heartbeat" not in e["event_type"] for e in decode_events(text))
    assert not app.state.streams._counts


def test_disconnected_stream_does_not_cancel_task(monkeypatch):
    async def disconnected(self):
        return True

    app = create_app(runtime=FakeRuntime(.001), rate_limits=False)
    with TestClient(app) as client:
        task = create_task(client, new_session(client))
        with monkeypatch.context() as patch:
            patch.setattr(Request, "is_disconnected", disconnected)
            assert client.get(task["events_url"]).text == ""
        assert not app.state.streams._counts
        assert wait_for_status(client, task)["status"] == "succeeded"


def test_terminal_commit_between_event_read_and_status_read_is_not_lost():
    class ConcurrentFinishStore(InMemoryTaskStore):
        def get_task(self, session_id, task_id):
            task = super().get_task(session_id, task_id)
            if task.status == TaskStatus.RUNNING:
                return self.finish(session_id, task_id, task.generation,
                                   TaskStatus.SUCCEEDED, "completed concurrently")
            return task

    with TestClient(create_app(store=ConcurrentFinishStore(), runtime=FakeRuntime(.1),
                              rate_limits=False)) as client:
        task = create_task(client, new_session(client))
        events = decode_events(client.get(task["events_url"]).text)
        assert events[-1]["event_type"] == "task.succeeded"
        assert events[-1]["payload"]["final_response"] == "completed concurrently"


def test_cancel_running_and_queued_is_idempotent():
    with TestClient(create_app(runtime=FakeRuntime(.1), max_concurrency=1, rate_limits=False)) as client:
        session = new_session(client)
        running = create_task(client, session)
        wait_for_status(client, running, {"running"})
        queued = create_task(client, session)
        assert client.post(queued["status_url"] + "/cancel", json={"reason": "stop"}).json()["status"] == "cancelled"
        assert client.post(queued["status_url"] + "/cancel").json()["status"] == "cancelled"
        response = client.post(running["status_url"] + "/cancel", json={})
        assert response.json()["status"] in {"cancelling", "cancelled"}
        assert wait_for_status(client, running)["status"] == "cancelled"
        assert client.post(running["status_url"] + "/cancel").status_code == 200
        assert client.post(running["status_url"] + "/resume").status_code == 409
        events = decode_events(client.get(running["events_url"]).text)
        assert events[-1]["event_type"] == "task.cancelled"
        assert not any(e["event_type"] == "task.succeeded" for e in events)


def test_cross_session_resources_are_not_found():
    with TestClient(create_app(runtime=FakeRuntime(.001), rate_limits=False)) as client:
        a, b = new_session(client), new_session(client)
        task = create_task(client, a)
        forbidden = task["status_url"].replace(a, b)
        for path in [forbidden, forbidden + "/events", forbidden + "/trace"]:
            response = client.get(path)
            assert response.status_code == 404
            assert a not in response.text
        for suffix in ["/cancel", "/resume"]:
            assert client.post(forbidden + suffix).status_code == 404
        assert client.post("/v1/sessions/missing/tasks", json={"problem": "x"}).status_code == 404


def test_api_idempotency_rejection_capacity_and_safe_validation():
    with TestClient(create_app(store=InMemoryTaskStore(max_queued=1), runtime=FakeRuntime(.5),
                              max_concurrency=1, rate_limits=False)) as client:
        session = new_session(client)
        task = create_task(client, session, headers={"Idempotency-Key": "stable"})
        replay = create_task(client, session, headers={"Idempotency-Key": "stable"})
        assert task["id"] == replay["id"]
        assert client.post(f"/v1/sessions/{session}/tasks", json={"problem": "changed"}, headers={"Idempotency-Key": "stable"}).status_code == 409
        wait_for_status(client, task, {"running"})
        create_task(client, session)
        response = client.post(f"/v1/sessions/{session}/tasks", json={"problem": "overflow"})
        assert response.status_code == 429 and response.headers["retry-after"] == "1"
        for payload in [{"problem": " "}, {"problem": "x", "runtime_mode": "legacy"},
                        {"problem": "x", "metadata": {"answer": "HIDDEN_REFERENCE"}},
                        {"problem": "x", "metadata": {"password": "PRIVATE_PASSWORD"}}]:
            response = client.post(f"/v1/sessions/{session}/tasks", json=payload)
            assert response.status_code == 400
            assert "HIDDEN_REFERENCE" not in response.text and "PRIVATE_PASSWORD" not in response.text
        assert client.post("/v1/sessions", json={"memory_token_limit": -1}).status_code == 400


class BrokenRuntime:
    name = "broken_test"

    def __init__(self, outcome):
        self.outcome = outcome

    async def run(self, context):
        context.progress("solve")
        if self.outcome == "raise":
            raise RuntimeError("sk-canarycredential123456789 C:\\private\\file.txt")
        if self.outcome == "timeout":
            await asyncio.sleep(10)
        if self.outcome == "recover":
            context.save_response("saved result")
            await asyncio.sleep(10)
        return RuntimeResult(self.outcome)


@pytest.mark.parametrize("outcome,expected", [("raise", "failed"), ("", "failed"),
                                                ("timeout", "failed"), ("recover", "succeeded")])
def test_failures_timeout_and_candidate_recovery(outcome, expected):
    with TestClient(create_app(runtime=BrokenRuntime(outcome), budget_seconds=.1,
                              finalize_reserve_seconds=.02, rate_limits=False)) as client:
        task = create_task(client, new_session(client))
        final = wait_for_status(client, task)
        assert final["status"] == expected
        trace = client.get(task["trace_url"]).text
        assert "sk-canary" not in json.dumps(final)
        assert "sk-canary" not in trace and "private" not in trace
        if outcome == "recover":
            assert final["final_response"] == "saved result"
        if outcome == "timeout":
            assert final["error_code"] == "task_deadline_exceeded"


def test_successful_output_is_sanitized_in_all_returns_and_memory():
    secret = "sk-canarycredential123456789"
    app = create_app(runtime=BrokenRuntime("answer " + secret), rate_limits=False)
    with TestClient(app) as client:
        session = new_session(client)
        task = create_task(client, session)
        final = wait_for_status(client, task)
        assert secret not in json.dumps(final)
        assert secret not in client.get(task["events_url"]).text
        assert secret not in client.get(task["trace_url"]).text
        assert secret not in app.state.store.get_session(session).messages[-1].content


def test_interruption_closes_stream_and_resume_uses_same_checkpoint():
    store = InMemoryTaskStore()
    app = create_app(store=store, runtime=FakeRuntime(.015), max_concurrency=1, rate_limits=False)
    with TestClient(app) as client:
        task = create_task(client, new_session(client))
        until = time.monotonic() + 3
        while not store.get_task(task["session_id"], task["id"]).checkpoint:
            assert time.monotonic() < until
            time.sleep(.005)
    interrupted = store.get_task(task["session_id"], task["id"])
    assert interrupted.status == TaskStatus.INTERRUPTED
    checkpoint = interrupted.checkpoint
    with TestClient(create_app(store=store, runtime=FakeRuntime(.001), rate_limits=False)) as client:
        stream = client.get(task["events_url"])
        assert decode_events(stream.text)[-1]["event_type"] == "task.interrupted"
        assert client.post(task["status_url"] + "/resume").status_code == 202
        assert wait_for_status(client, task)["status"] == "succeeded"
        completed = [event.payload["stage"] for event in store.get_task(task["session_id"], task["id"]).events if event.event_type == "stage.completed"]
        assert len(completed) == len(set(completed)) == 8
        assert checkpoint["completed_stage"] >= 0


def test_concurrency_and_worker_survives_cancel():
    class CountingRuntime:
        name = "concurrency_test"
        active = 0
        peak = 0

        def __init__(self):
            self.all_started = asyncio.Event()

        async def run(self, context):
            self.active += 1
            self.peak = max(self.peak, self.active)
            if self.active == 8:
                self.all_started.set()
            try:
                await asyncio.wait_for(self.all_started.wait(), 2)
                await asyncio.sleep(.04)
                return RuntimeResult("done")
            finally:
                self.active -= 1

    runtime = CountingRuntime()
    with TestClient(create_app(runtime=runtime, max_concurrency=8, rate_limits=False)) as client:
        tasks = [create_task(client, new_session(client)) for _ in range(20)]
        for task in tasks:
            assert wait_for_status(client, task)["status"] == "succeeded"
    assert runtime.peak == 8 and runtime.active == 0


def test_rate_limit_and_not_ready_paths():
    limiter = LocalRateLimiter()
    limiter.consume("test", "key", 1, .001)
    with pytest.raises(PlatformError, match="rate_limit_exceeded"):
        limiter.consume("test", "key", 1, .001)
    app = create_app()
    with TestClient(app) as client:
        for _ in range(5):
            assert client.post("/v1/sessions").status_code == 201
        assert client.post("/v1/sessions").status_code == 429
    app = create_app(rate_limits=False)
    with TestClient(app) as client:
        session = new_session(client)
        app.state.service.accepting = False
        assert client.get("/health/ready").status_code == 503
        assert client.post(f"/v1/sessions/{session}/tasks", json={"problem": "x"}).status_code == 503
        assert client.post(f"/v1/sessions/{session}/tasks/missing/resume").status_code == 503


def test_stream_capacity_rejection_and_release():
    budget = StreamBudget(total=3, per_task=2)
    budget.acquire("a")
    budget.acquire("a")
    with pytest.raises(PlatformError, match="sse_capacity_exceeded"):
        budget.acquire("a")
    budget.acquire("b")
    with pytest.raises(PlatformError, match="sse_capacity_exceeded"):
        budget.acquire("c")
    budget.release("a")
    budget.acquire("c")
    budget.release("a")
    budget.release("b")
    budget.release("c")
    assert not budget._counts
    app = create_app(runtime=FakeRuntime(.001), rate_limits=False)
    with TestClient(app) as client:
        task = create_task(client, new_session(client))
        for _ in range(8):
            app.state.streams.acquire(task["id"])
        response = client.get(task["events_url"])
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "sse_capacity_exceeded"
        for _ in range(8):
            app.state.streams.release(task["id"])
        assert client.get(task["events_url"]).status_code == 200


@pytest.mark.parametrize("kwargs", [{"max_concurrency": 0}, {"budget_seconds": 10},
                                   {"finalize_reserve_seconds": -1}, {"heartbeat_seconds": 0},
                                   {"heartbeat_seconds": 16}, {"poll_seconds": 0}])
def test_invalid_service_configuration(kwargs):
    with pytest.raises(ValueError):
        create_app(**kwargs)


def test_service_start_is_idempotent_and_cancel_without_execution():
    async def scenario():
        store = InMemoryTaskStore()
        service = TaskService(store, FakeRuntime(), max_concurrency=1)
        session = store.create_session(0)
        task = store.create_task(session.id, "queued", {}, "fake", None)[0]
        await service.start()
        await service.start()
        assert len(service._workers) == 1
        assert service.cancel(session.id, task.id).status == TaskStatus.CANCELLED
        await service.stop()
    asyncio.run(scenario())
