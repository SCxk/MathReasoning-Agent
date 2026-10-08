"""History pagination and restart visibility; fixtures are not model quality data."""

import base64
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
import fakeredis
from redis.exceptions import ConnectionError

from agent_platform.app import create_app
from agent_platform.history import cursor_member, next_cursor
from agent_platform.models import PlatformError, TaskStatus
from agent_platform.redis_store import RedisTaskStore
from agent_platform.runtime import FakeRuntime
from agent_platform.storage import InMemoryTaskStore


@pytest.fixture(params=["memory", "redis"])
def store(request):
    if request.param == "memory":
        return InMemoryTaskStore()
    return RedisTaskStore(fakeredis.FakeRedis(decode_responses=True), require_aof=False)


def finished(store, session, problem="History fixture", key=None):
    task, _ = store.create_task(session, problem, {}, "fake", key)
    started = store.start(session, task.id, 1200)
    store.progress(session, task.id, started.generation, "solve", True, {"candidate": "private-state"})
    store.finish(session, task.id, started.generation, TaskStatus.SUCCEEDED, "Public fixture answer")
    return task


def test_paged_sessions_tasks_and_idempotency(store):
    sessions = [store.create_session(100) for _ in range(5)]
    values = [finished(store, sessions[0].id, f"Question {number}", str(number)) for number in range(7)]
    duplicate, created = store.create_task(sessions[0].id, "Question 0", {}, "fake", "0")
    assert not created and duplicate.id == values[0].id
    ids, cursor = [], None
    while True:
        page = store.list_sessions(2, cursor)
        ids.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert ids == [session.id for session in reversed(sessions)]
    summary = store.list_sessions(50)["items"][-1]
    assert summary["title"] == "Question 0" and summary["task_count"] == 7
    assert "messages" not in summary
    tasks, cursor = store.list_tasks(sessions[0].id, 3)
    result = list(tasks)
    # Inserting a newer item must not shift the remaining older pages.
    finished(store, sessions[0].id, "New question")
    while cursor:
        tasks, cursor = store.list_tasks(sessions[0].id, 3, cursor)
        result.extend(tasks)
    assert [task.id for task in result] == [task.id for task in reversed(values)]


def test_task_cursor_is_bound_to_session(store):
    first, second = [store.create_session(0) for _ in range(2)]
    finished(store, first.id)
    finished(store, first.id)
    _, cursor = store.list_tasks(first.id, 1)
    with pytest.raises(PlatformError, match="invalid_cursor"):
        store.list_tasks(second.id, 1, cursor)
    with pytest.raises(PlatformError, match="invalid_cursor"):
        store.list_sessions(1, cursor)
    with pytest.raises(PlatformError, match="session_not_found"):
        store.list_tasks("missing", 1)
    assert store.list_tasks(second.id, 5) == ([], None)


@pytest.mark.parametrize("cursor", ["", "bad!", "x" * 513, base64.b64encode(b"[]").decode(),
    base64.b64encode(b'{"scope":"sessions","member":null}').decode(),
    next_cursor("99999999999999999999:" + "a" * 36, "sessions")])
def test_invalid_cursor(cursor):
    with pytest.raises(PlatformError, match="invalid_cursor"):
        cursor_member(cursor, "sessions")


def test_public_api_history_does_not_expose_internal_state(store):
    session = store.create_session(100)
    task = finished(store, session.id, "api_key=secret-value")
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), rate_limits=False)) as client:
        assert client.get("/health/ready").json()["server_history"] is True
        response = client.get("/v1/sessions")
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["items"][0]["task_count"] == 1
        detail = client.get(f"/v1/sessions/{session.id}")
        assert detail.json()["memory_token_limit"] == 100 and "messages" not in detail.json()
        response = client.get(f"/v1/sessions/{session.id}/tasks")
        row = response.json()["items"][0]
        assert row["id"] == task.id and row["final_response"] == "Public fixture answer"
        assert row["checkpoint_available"]
        assert not {"checkpoint", "metadata", "tool_calls", "memory", "events"}.intersection(row)
        assert "secret-value" not in json.dumps(response.json())
        assert "private-state" not in response.text
        assert response.headers["cache-control"] == "no-store"
        for route in ("/v1/sessions", f"/v1/sessions/{session.id}/tasks"):
            for query in ("limit=0", "limit=51", "cursor=bad!"):
                assert client.get(route + "?" + query).status_code == 400
        assert client.get("/v1/sessions/missing/tasks").status_code == 404


def test_redis_reopened_history_indexes_and_outage():
    client = fakeredis.FakeRedis(decode_responses=True)
    first = RedisTaskStore(client, namespace="chat", require_aof=False)
    session = first.create_session(100)
    task = finished(first, session.id)
    second = RedisTaskStore(client, namespace="chat", require_aof=False)
    assert second.list_sessions(10)["items"][0]["id"] == session.id
    assert second.list_tasks(session.id, 10)[0][0].final_response == "Public fixture answer"
    assert second.get_task(session.id, task.id).checkpoint["candidate"] == "private-state"
    foreign = RedisTaskStore(client, namespace="other", require_aof=False)
    assert foreign.list_sessions(10) == {"items": [], "next_cursor": None}
    with patch.object(client, "zrevrangebylex", side_effect=ConnectionError()), pytest.raises(PlatformError, match="storage_unavailable"):
        second.list_sessions(10)
    with patch.object(client, "mget", side_effect=ConnectionError()), pytest.raises(PlatformError, match="storage_unavailable"):
        second.list_sessions(10)
    client.delete(second.key(f"summary:{session.id}"))
    with pytest.raises(PlatformError, match="history_index_missing"):
        second.list_sessions(10)
    with pytest.raises(PlatformError, match="history_index_missing"):
        second.create_task(session.id, "New fixture", {}, "fake", None)


def test_history_outage_api_does_not_return_fake_empty_list():
    store = RedisTaskStore(fakeredis.FakeRedis(decode_responses=True), require_aof=False)
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), rate_limits=False)) as client:
        with patch.object(store.client, "zrevrangebylex", side_effect=ConnectionError()):
            response = client.get("/v1/sessions")
            assert response.status_code == 503
            assert response.json() == {"error": {"code": "storage_unavailable"}}


def test_history_rate_limit_is_enforced():
    with TestClient(create_app(runtime=FakeRuntime(0))) as client:
        with patch("agent_platform.app.LocalRateLimiter.consume", side_effect=PlatformError("rate_limit_exceeded", 429)):
            response = client.get("/v1/sessions")
            assert response.status_code == 429 and response.headers["retry-after"] == "1"


def test_equal_timestamp_cursor_orders_by_id_without_duplicates():
    from datetime import datetime, timezone
    from agent_platform.history import member, page_cursor

    created = datetime(2026, 10, 5, tzinfo=timezone.utc)
    values = sorted([member(created, "00000000-0000-4000-8000-00000000000" + str(index))
                     for index in range(5)], reverse=True)
    cursor = page_cursor(values, 2, "sessions")
    assert cursor_member(cursor, "sessions") == values[1]
    assert [value for value in values if value < cursor_member(cursor, "sessions")] == values[2:]
