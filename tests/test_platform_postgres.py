"""Run against an explicitly supplied scratch PostgreSQL URL; each test owns its schema."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
import threading
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import DropSchema

from agent_platform.database import database, migrate
from agent_platform.models import PlatformError, TaskStatus, utc_now
from agent_platform.postgres_documents import AdvisoryIndexLock, PostgresDocumentCatalog
from agent_platform.postgres_store import PostgresTaskStore


@pytest.fixture
def stores():
    url = os.environ.get("MATHS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("MATHS_TEST_DATABASE_URL must name a disposable integration database")
    namespace = "test_m6_" + uuid4().hex[:16]
    engine, metadata = database(url, namespace)
    migrate(engine, metadata)
    migrate(engine, metadata)
    try:
        yield [PostgresTaskStore(engine, metadata), PostgresTaskStore(engine, metadata)]
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(namespace, cascade=True))
        engine.dispose()


def task(store, session=None, **kwargs):
    session = session or store.create_session(100).id
    value, _ = store.create_task(session, "generic fixture", {}, "fake", kwargs.get("key"))
    return value


def test_question_lookup_is_scoped_readonly_and_excludes_session_memory(stores):
    first, second = stores
    previous = task(first)
    value, _ = first.create_task(previous.session_id, "question fixture", {"_question_source": {"batch_id": "fixture"}}, "fake", "question-key")
    assert value.memory == ()
    assert second.lookup_submission(previous.session_id, "question-key").id == value.id
    assert second.lookup_submission(previous.session_id, "missing") is None
    assert second.lookup_submission(first.create_session(100).id, "question-key") is None
    assert len(second.list_tasks(previous.session_id, 20)[0]) == 2


def test_history_pagination_reopen_and_scoping(stores):
    first, second = stores
    sessions = [first.create_session(100) for _ in range(3)]
    values = [task(first, sessions[0].id) for _ in range(5)]
    page = second.list_sessions(2)
    assert [row["id"] for row in page["items"]] == [item.id for item in reversed(sessions[1:])]
    remainder = second.list_sessions(2, page["next_cursor"])
    assert remainder["items"][0]["task_count"] == 5
    assert remainder["items"][0]["title"] == "generic fixture"
    assert remainder["next_cursor"] is None
    rows, cursor = second.list_tasks(sessions[0].id, 2)
    found = list(rows)
    with pytest.raises(PlatformError, match="invalid_cursor"):
        second.list_tasks(sessions[1].id, 2, cursor)
    with pytest.raises(PlatformError, match="session_not_found"):
        second.list_tasks("missing", 2)
    while cursor:
        rows, cursor = second.list_tasks(sessions[0].id, 2, cursor)
        found.extend(rows)
    assert [value.id for value in found] == [value.id for value in reversed(values)]


def test_new_task_validation_is_atomic_and_skipped_for_accepted_retry(stores):
    first, second = stores
    original = task(first, key="accepted")
    def reject():
        raise PlatformError("document_not_ready", 409)
    duplicate, created = second.create_task(original.session_id, original.problem, {}, "fake", "accepted", reject)
    assert duplicate.id == original.id and not created
    with pytest.raises(PlatformError, match="document_not_ready"):
        second.create_task(original.session_id, "new problem", {}, "fake", "new", reject)
    assert len(second.get_session(original.session_id).messages) == 1
    assert len(second.list_tasks(original.session_id, 10)[0]) == 1


def test_document_list_pagination_and_session_scoping(stores):
    from test_platform_rag import document
    first, second = stores
    session, foreign = first.create_session(0), first.create_session(0)
    catalog = PostgresDocumentCatalog(first.engine, first.metadata)
    reopened = PostgresDocumentCatalog(second.engine, second.metadata)
    docs = [document(session.id, text=f"pagination fixture {index}") for index in range(5)]
    for doc in docs:
        catalog.reserve(doc)
    catalog.reserve(document(foreign.id))
    rows, cursor = reopened.list_page(session.id, 2)
    found = list(rows)
    with pytest.raises(PlatformError, match="invalid_cursor"):
        reopened.list_page(foreign.id, 2, cursor)
    while cursor:
        rows, cursor = reopened.list_page(session.id, 2, cursor)
        found.extend(rows)
    assert [doc.id for doc in found] == [doc.id for doc in reversed(docs)]


def test_atomic_lifecycle_checkpoint_ledger_fencing_and_memory(stores):
    first, second = stores
    assert first.ready()
    value = task(first, key="same")
    duplicate, created = second.create_task(value.session_id, value.problem, {}, "fake", "same")
    assert duplicate.id == value.id and not created
    claimed = first.start(value.session_id, value.id, 1200)
    assert second.start(value.session_id, value.id, 1200) is None
    first.progress(
        value.session_id, value.id, claimed.generation, "solve", True, {"candidate": "kept"}
    )
    first.record(
        value.session_id,
        value.id,
        claimed.generation,
        "solve",
        "model.started",
        {"operation_id": "operation", "call_type": "solver"},
    )
    entry = {"stage_id": "tool", "arguments_hash": "a", "result": {"ok": True}, "attempts": []}
    first.tool_record(
        value.session_id,
        value.id,
        claimed.generation,
        "call",
        entry,
        "tool.completed",
        {"name": "math_verify"},
    )
    first.finish(value.session_id, value.id, claimed.generation, TaskStatus.INTERRUPTED)
    restored = second.get_task(value.session_id, value.id)
    assert restored.checkpoint == {"candidate": "kept"}
    assert restored.model_calls == {"solver": 1} and restored.tool_calls["call"] == entry
    assert any(
        e.event_type == "model.interrupted"
        for e in second.events_after(value.session_id, value.id, 0)
    )
    second.resume(value.session_id, value.id)
    new = second.start(value.session_id, value.id, 1200)
    assert new.deadline_at == claimed.deadline_at
    first.finish(value.session_id, value.id, claimed.generation, TaskStatus.SUCCEEDED, "stale")
    with pytest.raises(PlatformError, match="stale_execution"):
        first.record(value.session_id, value.id, claimed.generation, "solve", "model.started", {})
    second.finish(value.session_id, value.id, new.generation, TaskStatus.SUCCEEDED, "kept")
    assert second.get_session(value.session_id).messages[-1].content == "kept"
    events = second.events_after(value.session_id, value.id, 0)
    assert [e.sequence for e in events] == list(range(1, len(events) + 1))
    assert len(second.get_session(value.session_id).messages) == 2
    assert sum(
        row["value"] for row in second.metric_rows() if row["name"] == "maths_events_total"
    ) == len(events)


def test_rollback_retains_state_events_and_counters(stores, monkeypatch):
    first, second = stores
    value = task(first)
    claimed = first.start(value.session_id, value.id, 1200)
    before = second.get_task(value.session_id, value.id)
    metrics = list(second.metric_rows())
    monkeypatch.setattr(
        first, "_event_metrics", lambda *args: (_ for _ in ()).throw(SQLAlchemyError("secret"))
    )
    with pytest.raises(PlatformError, match="storage_unavailable"):
        first.progress(
            value.session_id, value.id, claimed.generation, "solve", True, {"candidate": "lost"}
        )
    after = second.get_task(value.session_id, value.id)
    assert after.checkpoint == before.checkpoint and after.event_sequence == before.event_sequence
    assert list(second.metric_rows()) == metrics


def test_concurrent_idempotency_queue_capacity_and_eight_claims(stores):
    first, second = stores
    session = first.create_session(0).id
    with ThreadPoolExecutor(max_workers=10) as pool:
        values = list(
            pool.map(
                lambda i: stores[i % 2].create_task(session, "fixture", {}, "fake", "same"),
                range(20),
            )
        )
    assert len({value.id for value, _ in values}) == 1
    assert sum(created for _, created in values) == 1
    first.max_queued = second.max_queued = 10
    for _ in range(9):
        task(first, session)
    with pytest.raises(PlatformError, match="queue_capacity_exceeded"):
        task(second, session)
    queued = first.list_queued()
    with ThreadPoolExecutor(max_workers=10) as pool:
        claims = list(pool.map(lambda value: second.start(session, value.id, 1200), queued))
    assert sum(value is not None for value in claims) == 8
    assert first.status_counts() == {"queued": 2, "running": 8}


def test_lease_expiry_resume_discovery_outbox_and_cancel(stores):
    first, second = stores
    value = task(first)
    claimed = first.start(value.session_id, value.id, 1200)
    first.progress(
        value.session_id, value.id, claimed.generation, "solve", True, {"next_stage": "tool"}
    )
    table = first.table("tasks")
    with first.engine.begin() as connection:
        data = connection.execute(select(table.c.data).where(table.c.id == value.id)).scalar_one()
        expired = utc_now() - timedelta(seconds=1)
        data["lease_until"] = expired.isoformat()
        connection.execute(
            update(table).where(table.c.id == value.id).values(data=data, lease_until=expired)
        )
    second.recover_expired()
    assert second.list_interrupted()[0].id == value.id
    second.resume(value.session_id, value.id)
    due = second.dispatch_due("fake")
    assert [v.id for v in due] == [value.id] and due[0].resume_requested
    assert second.dispatch_due("fake") == []
    assert second.dispatch_due("other") == []
    assert second.queue_position(value.id) == 1
    pending = first.unpublished_events()
    first.mark_published(pending[0])
    assert len(second.unpublished_events()) == len(pending) - 1
    second.cancel(value.session_id, value.id)
    assert second.get_task(value.session_id, value.id).status == TaskStatus.CANCELLED
    with pytest.raises(PlatformError, match="cursor_ahead"):
        second.events_after(value.session_id, value.id, 1000)


def test_hundred_paired_session_task_checkpoint_event_and_memory_isolation(stores):
    first, second = stores
    for index in range(100):
        own = task(first)
        foreign = first.create_session(100)
        claimed = first.start(own.session_id, own.id, 1200)
        first.progress(
            own.session_id, own.id, claimed.generation, "solve", True, {"candidate": str(index)}
        )
        first.finish(own.session_id, own.id, claimed.generation, TaskStatus.SUCCEEDED, str(index))
        for access in (second.get_task, lambda s, t: second.events_after(s, t, 0)):
            with pytest.raises(PlatformError, match="task_not_found"):
                access(foreign.id, own.id)
        assert second.get_session(foreign.id).messages == []
        assert second.get_task(own.session_id, own.id).checkpoint["candidate"] == str(index)


def test_document_catalog_publication_and_cross_process_reader_lock(stores):
    from agent_platform.rag.models import Document

    first = stores[0]
    session = first.create_session(100).id
    catalog = PostgresDocumentCatalog(first.engine, first.metadata)
    document = Document(
        id=str(uuid4()),
        session_id=session,
        original_name="fixture.md",
        media_type="text/markdown",
        size_bytes=10,
        content_hash="a" * 64,
        storage_key="blobs/fixture",
        created_at=utc_now().isoformat(),
        expires_at=(utc_now() + timedelta(days=90)).isoformat(),
    )
    catalog.reserve(document)
    with pytest.raises(PlatformError, match="duplicate_document"):
        catalog.reserve(document)
    assert catalog.get(session, document.id).status == "indexing"
    chunk = {
        "id": str(uuid4()),
        "document_id": document.id,
        "source_metadata": {"parser_version": "parser-test"},
    }
    catalog.activate(document, [chunk], [[1.0, 0.0]], "collection", "index-test", "hash", 1)
    assert catalog.snapshot(session) == ("collection", "index-test", "hash")
    assert catalog.chunk_records(session) == [(chunk, [1.0, 0.0])]
    assert catalog.chunk_records(str(uuid4())) == []
    with pytest.raises(PlatformError, match="document_not_found"):
        catalog.get(str(uuid4()), document.id)
    reader = AdvisoryIndexLock(first.engine, first.namespace, shared=True)
    acquired = threading.Event()

    def acquire_reader():
        with reader:
            acquired.set()

    with catalog.index_lock:
        with catalog.index_lock:
            thread = threading.Thread(target=acquire_reader)
            thread.start()
            assert not acquired.wait(0.05)
    thread.join(2)
    assert acquired.is_set()
    catalog.expire(document)
    assert catalog.chunk_records(session) == []
    assert catalog.collections() == {"collection"}
    assert catalog.referenced_blobs() == {"blobs/fixture"}


def test_recovery_reservation_and_error_sanitizing(stores):
    first = stores[0]
    running = []
    for _ in range(7):
        value = task(first)
        running.append(first.start(value.session_id, value.id, 1200))
    interrupted = running.pop()
    first.finish(
        interrupted.session_id, interrupted.id, interrupted.generation, TaskStatus.INTERRUPTED
    )
    first.resume(interrupted.session_id, interrupted.id)
    normal = task(first)
    extra = task(first)
    first.start(extra.session_id, extra.id, 1200)
    assert first.start(normal.session_id, normal.id, 1200) is None
    assert first.start(interrupted.session_id, interrupted.id, 1200) is not None
    with pytest.raises(PlatformError, match="session_not_found"):
        first.get_session(str(uuid4()))
    assert "password" not in json.dumps(
        [e.model_dump(mode="json") for e in first.unpublished_events()]
    )


def test_first_status_once_and_terminal_retention(stores):
    first, second = stores
    value = task(first)
    first.observe_first_status(value.session_id, value.id, 0.01)
    second.observe_first_status(value.session_id, value.id, 20)
    observed = [
        row for row in first.metric_rows() if row["name"] == "maths_task_first_status_seconds_count"
    ]
    assert observed[0]["value"] == 1
    claimed = first.start(value.session_id, value.id, 1200)
    first.finish(value.session_id, value.id, claimed.generation, TaskStatus.SUCCEEDED, "done")
    assert first.cleanup() == 0
    table = first.table("tasks")
    with first.engine.begin() as connection:
        data = connection.execute(select(table.c.data).where(table.c.id == value.id)).scalar_one()
        data["finished_at"] = (utc_now() - timedelta(days=31)).isoformat()
        connection.execute(update(table).where(table.c.id == value.id).values(data=data))
    assert second.cleanup() == 1
    assert second.get_session(value.session_id).messages == []
    assert second.unpublished_events() == []
    with pytest.raises(PlatformError, match="task_not_found"):
        second.get_task(value.session_id, value.id)
