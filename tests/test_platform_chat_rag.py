"""Chat attachment and citation contracts; synthetic passages are not evaluation labels."""

from datetime import timedelta
import json
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from agent_platform.app import create_app
from agent_platform.models import TaskStatus, utc_now
from agent_platform.rag.service import DocumentService
from agent_platform.references import public_references
from agent_platform.runtime import FakeRuntime
from agent_platform.storage import InMemoryTaskStore
from test_platform_rag import TestEmbedding, document, parsed


def passage(doc, **changes):
    return {"chunk_id": str(uuid4()), "document_id": doc.id, "rank": 1,
            "text": "$x^2$ is a synthetic excerpt", "page_start": 1, "page_end": 2,
            "scores": {"rerank": .5}, "source_metadata": {
                "title": doc.original_name, "heading": "Algebra", "domain": None,
                "problem_type": None, "source": None, "parser_version": "test-v1",
                "index_version": "test-v1", "content_hash": doc.content_hash}, **changes}


def test_scoped_document_list_pagination_and_expiry(tmp_path):
    service = DocumentService(tmp_path, TestEmbedding())
    store = InMemoryTaskStore()
    session, foreign = store.create_session(0), store.create_session(0)
    values = [document(session.id, text=f"synthetic {index}") for index in range(5)]
    for doc in values:
        service.catalog.reserve(doc)
    service.catalog.reserve(document(foreign.id))
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), documents=service, rate_limits=False)) as client:
        # No blobs: the ingestion worker correctly marks these reservations failed.
        route = f"/v1/sessions/{session.id}/documents"
        response = client.get(route, params={"limit": 2})
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        page = response.json()
        rows = list(page["items"])
        cursor = page["next_cursor"]
        assert client.get(f"/v1/sessions/{foreign.id}/documents", params={"cursor": cursor}).status_code == 400
        while cursor:
            page = client.get(route, params={"limit": 2, "cursor": cursor}).json()
            rows.extend(page["items"])
            cursor = page["next_cursor"]
        assert [row["id"] for row in rows] == [doc.id for doc in reversed(values)]
        assert all("storage_key" not in row and row["session_id"] == session.id for row in rows)
        for params in ({"limit": 0}, {"limit": 51}, {"cursor": "bad!"}):
            assert client.get(route, params=params).status_code == 400
        assert client.get("/v1/sessions/missing/documents").status_code == 404
        expired = document(session.id).model_copy(update={"expires_at": (utc_now() - timedelta(days=1)).isoformat()})
        assert service._projection(expired)["status"] == "expired"


@pytest.mark.parametrize("selection", [None, "invalid", ["not-a-uuid"], [str(uuid4())] * 101])
def test_invalid_document_selection_rejected(selection):
    with TestClient(create_app(runtime=FakeRuntime(0), rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        response = client.post(f"/v1/sessions/{session}/tasks", json={"problem": "fixture", "metadata": {"document_ids": selection}})
        assert response.status_code == 400


def test_selected_attachment_must_be_ready_and_in_session(tmp_path):
    service = DocumentService(tmp_path, TestEmbedding())
    store = InMemoryTaskStore()
    session = store.create_session(0)
    ready = document(session.id)
    service.catalog.reserve(ready)
    service.index.ingest(ready, parsed())
    failed = document(session.id, text="failed fixture")
    service.catalog.reserve(failed)
    service.catalog.fail(failed, "indexing_failed")
    foreign = document()
    service.catalog.reserve(foreign)
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), documents=service, rate_limits=False)) as client:
        route = f"/v1/sessions/{session.id}/tasks"
        for identifier, status in [(ready.id, 202), (failed.id, 409), (foreign.id, 404)]:
            response = client.post(route, json={"problem": "fixture", "metadata": {"document_ids": [identifier]}})
            assert response.status_code == status
        assert client.post(route, json={"problem": "fixture", "metadata": {"document_ids": []}}).status_code == 202


def test_document_list_without_rag_is_unavailable():
    with TestClient(create_app(runtime=FakeRuntime(0), rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        assert client.get(f"/v1/sessions/{session}/documents").status_code == 503
        response = client.post(f"/v1/sessions/{session}/tasks", json={"problem": "fixture", "metadata": {"document_ids": [str(uuid4())]}})
        assert response.status_code == 503


def test_reference_snapshot_is_bounded_sanitized_and_not_inferred_from_failed_draft():
    store = InMemoryTaskStore()
    session = store.create_session(0)
    doc = document(session.id)
    part = passage(doc, text="api_key=private-value $x^2$")
    task, _ = store.create_task(session.id, "fixture", {"document_ids": [doc.id]}, "fake", None)
    task.tool_calls = {"call": {"tool_name": "document_search", "result": {"status": "succeeded", "value": {"passages": [part]}}}}
    task.checkpoint = {"draft": "failed draft cites " + part["chunk_id"]}
    task.final_response = "Accepted response without a citation"
    rows = public_references(task)
    assert rows[0]["citation_status"] == "retrieved"
    assert "private-value" not in json.dumps(rows)
    assert rows[0]["page_start"] == 1 and rows[0]["title"] == doc.original_name
    task.final_response += " [" + part["chunk_id"].upper() + "]"
    assert public_references(task)[0]["citation_status"] == "mentioned_in_answer"
    task.metadata["document_ids"] = []
    assert public_references(task) == []
    task.metadata = {}
    task.tool_calls["call"]["result"]["status"] = "failed"
    assert public_references(task) == []
    task.tool_calls["call"]["result"] = {"status": "succeeded", "value": {"passages": [{"invalid": True}]}}
    assert public_references(task) == []
    for index in range(3):
        task.tool_calls[str(index)] = {"tool_name": "document_search", "result": {"status": "succeeded",
            "value": {"passages": [passage(doc) for _ in range(20)]}}}
    assert len(public_references(task)) == 20


def test_references_survive_public_task_and_history_loading():
    store = InMemoryTaskStore()
    session = store.create_session(0)
    task, _ = store.create_task(session.id, "fixture", {}, "fake", None)
    part = passage(document(session.id))
    started = store.start(session.id, task.id, 1200)
    entry = {"tool_name": "document_search", "stage_id": "retrieve", "arguments_hash": "hash",
             "result": {"status": "succeeded", "value": {"passages": [part]}}, "attempts": []}
    store.tool_record(session.id, task.id, started.generation, "call", entry, "tool.completed", {})
    store.finish(session.id, task.id, started.generation, TaskStatus.SUCCEEDED, part["chunk_id"])
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), rate_limits=False)) as client:
        route = f"/v1/sessions/{session.id}/tasks"
        current = client.get(route + "/" + task.id).json()
        history = client.get(route).json()["items"][0]
        assert current["references"] == history["references"]
        assert current["references"][0]["citation_status"] == "mentioned_in_answer"


def test_tool_requests_cannot_override_selected_documents():
    import asyncio
    from agent_platform.tools.registry import ToolRegistry
    from agent_platform.tools.schemas import ToolInvocation
    from test_platform_graph import context
    from unittest.mock import AsyncMock

    async def run():
        ctx, _, _ = context()
        ctx.session_id = str(uuid4())
        selected = str(uuid4())
        ctx.metadata["document_ids"] = [selected]
        tools = ToolRegistry()
        tools.local.invoke = AsyncMock(return_value={"status": "succeeded", "value": {"passages": []}})
        args = {"query": "fixture", "session_id": ctx.session_id}
        request = ToolInvocation(call_id="one", task_id=ctx.task_id, stage_id="solve", tool_name="document_search", arguments=args, timeout_ms=1000)
        assert (await tools.invoke(request, ctx)).status == "succeeded"
        assert tools.local.invoke.call_args.args[1]["document_ids"] == [selected]
        request = request.model_copy(update={"call_id": "two", "arguments": {**args, "document_ids": [str(uuid4())]}})
        assert (await tools.invoke(request, ctx)).error_code == "scope_violation"
        assert tools.local.invoke.call_count == 1
    asyncio.run(run())


def test_accepted_retry_survives_attachment_expiry(tmp_path):
    service = DocumentService(tmp_path, TestEmbedding())
    store = InMemoryTaskStore()
    session = store.create_session(0)
    doc = document(session.id)
    service.catalog.reserve(doc)
    service.index.ingest(doc, parsed())
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), documents=service, rate_limits=False)) as client:
        route = f"/v1/sessions/{session.id}/tasks"
        body = {"problem": "fixture", "metadata": {"document_ids": [doc.id]}}
        headers = {"Idempotency-Key": "accepted"}
        original = client.post(route, json=body, headers=headers)
        assert original.status_code == 202
        service.catalog.expire(doc)
        retry = client.post(route, json=body, headers=headers)
        assert retry.status_code == 202 and retry.json()["id"] == original.json()["id"]
        conflict = client.post(route, json={**body, "problem": "changed"}, headers=headers)
        assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "idempotency_conflict"
        assert client.post(route, json=body).status_code == 409
