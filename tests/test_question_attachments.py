"""Synthetic upload/protocol fixtures, never a mathematical-quality benchmark."""

import asyncio
import io
import json
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from agent_platform.app import create_app
from agent_platform.models import PlatformError, TaskStatus
from agent_platform.question_batches import QuestionCatalog
from agent_platform.questions_parser import SOURCE_KEY, INSTRUCTION_KEY, parse_questions, split_questions
from agent_platform.rag.isolation import isolated_parse
from agent_platform.rag.parser import ParseRejected
from agent_platform.runtime import FakeRuntime
from agent_platform.storage import InMemoryTaskStore


TEXT = "# Exercise sheet\nShared condition: variables are real.\n\n## Question 1\nSolve $x+1=3$.\n\n## Question 2\nCompute $2^3$.\n"


def upload(client, session, content=TEXT, **kwargs):
    return client.post(f"/v1/sessions/{session}/question-batches",
                       files={"file": (kwargs.pop("filename", "questions.md"), content.encode() if isinstance(content, str) else content,
                                       kwargs.pop("mime", "text/markdown"))}, data=kwargs)


def wait_batch(client, session, identifier, status="completed"):
    end = time.monotonic() + 10
    while time.monotonic() < end:
        response = client.get(f"/v1/sessions/{session}/question-batches/{identifier}")
        assert response.status_code == 200
        value = response.json()
        if value["status"] == status:
            return value
        time.sleep(.05)
    raise AssertionError(value)


def start_batch(client, session, identifier, prompt="Explain the solution.", style="auto"):
    wait_batch(client, session, identifier, "ready")
    response = client.post(f"/v1/sessions/{session}/question-batches/{identifier}/start",
                           json={"prompt": prompt, "response_style": style})
    assert response.status_code == 202
    return response.json()


@pytest.mark.parametrize("content,method,count", [
    (TEXT, "question_labels", 2),
    ("第1题：求 $1+1$。\n第2题：求 $2+2$。", "question_labels", 2),
    ("1. Compute a value.\n   1. Keep this subpart.\n   2. And this one.\n2. Prove a statement.", "numbered", 2),
    ("1、第一道题。\n2、第二道题。", "numbered", 2),
    ("Find the derivative of $x^2$.", "single", 1),
    ("## Problem 1\n```text\nQuestion 9: not a question\n```\n$$\n1. x+y\n$$\n## Problem 2\nSolve.", "question_labels", 2),
])
def test_split_shapes_preserve_question_text(content, method, count):
    parsed = split_questions([content])
    assert parsed.split_method == method and len(parsed.questions) == count
    if content == TEXT:
        assert all("Shared condition" in question.problem for question in parsed.questions)
        assert "Compute $2^3$" not in parsed.questions[0].problem
    if "subpart" in content:
        assert "Keep this subpart" in parsed.questions[0].problem


@pytest.mark.parametrize("content,code", [
    ("", "no_extractable_text"),
    ("## Question 1\n", "empty_question"),
    ("## Question 1\nSolve.\n### Question 2\nSolve.", "ambiguous_question_structure"),
    ("## Topic A\nText.\n## Topic B\nText.", "ambiguous_question_structure"),
    ("1. Solve.\n\n1. Solve another.", "ambiguous_question_structure"),
    ("## Question 1\nSolve.\n## Answer\nHidden solution.", "question_file_contains_solutions"),
    ("第1题：求值。\n答案：已给出。", "question_file_contains_solutions"),
    ("## Question 1\nSolve.\n## Question 1\nAnother problem.", "ambiguous_question_structure"),
    ("$$\nx+y\n", "unclosed_formula_or_fence"),
    ("```text\nQuestion 1\n", "unclosed_formula_or_fence"),
    ("\ufffd broken extraction", "unreliable_question_text"),
    ("x" * 24001, "question_too_long"),
    ("\n".join(f"## Question {i}\nCompute a value." for i in range(1, 22)), "too_many_questions"),
])
def test_fail_closed_question_shapes(content, code):
    with pytest.raises(ParseRejected, match=code):
        split_questions([content])


def test_pdf_page_provenance_and_shared_stem():
    parsed = split_questions(["Shared assumption.\nQuestion 1: first part.",
                             "Continuation of question one.", "Question 2: second problem."], pdf=True)
    assert parsed.questions[0].page_start == 1 and parsed.questions[0].page_end == 2
    assert parsed.questions[1].page_start == parsed.questions[1].page_end == 3
    assert "Shared assumption" in parsed.questions[1].problem


def test_real_isolated_pdf_and_markdown_parser(tmp_path):
    from scripts.smoke_platform_m5 import pdf_file
    pdf = pdf_file()
    path = tmp_path / "questions.pdf"
    path.write_bytes(pdf.file.read())
    value = asyncio.run(isolated_parse(path, "application/pdf", questions=True))
    assert value.questions[0].page_start == 1 and "Geometry" in value.questions[0].problem
    markdown = tmp_path / "questions.md"
    markdown.write_text(TEXT, encoding="utf-8")
    assert len(asyncio.run(isolated_parse(markdown, "text/markdown", questions=True)).questions) == 2
    path.write_bytes(b"bad PDF")
    with pytest.raises(Exception):
        parse_questions(path, "application/pdf")
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=600, height=800)
    buffer = io.BytesIO()
    writer.write(buffer)
    path.write_bytes(buffer.getvalue())
    with pytest.raises(ParseRejected, match="no_extractable_text"):
        parse_questions(path, "application/pdf")


def test_upload_waits_then_manual_start_solves_sequentially_and_restores_history(tmp_path):
    store = InMemoryTaskStore()
    with TestClient(create_app(store=store, runtime=FakeRuntime(.01), question_dir=tmp_path, rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        foreign = client.post("/v1/sessions", json={}).json()["id"]
        response = upload(client, session, response_style="detailed")
        assert response.status_code == 202 and response.json()["status"] == "parsing"
        identifier = response.json()["id"]
        assert client.get("/health/ready").json()["question_attachments"]
        assert client.get("/health/ready").json()["question_submission"] == "explicit_send"
        preview = wait_batch(client, session, identifier, "ready")
        assert not preview["user_instruction"]
        time.sleep(.6)
        assert store.list_tasks(session, 10)[0] == []
        start_batch(client, session, identifier, style="detailed")
        item = wait_batch(client, session, identifier)
        assert item["question_count"] == item["counts"]["succeeded"] == 2
        first, second = [store.get_task(session, row["task"]["id"]) for row in item["questions"]]
        assert first.finished_at <= second.started_at
        assert first.memory == second.memory == ()
        assert first.metadata[SOURCE_KEY]["batch_id"] == identifier
        assert first.metadata["document_ids"] == []
        assert first.metadata["_chat_response_style"] == "detailed"
        assert first.metadata[INSTRUCTION_KEY] == second.metadata[INSTRUCTION_KEY] == item["user_instruction"] == "Explain the solution."
        assert first.problem == preview["questions"][0]["problem"]
        public = client.get(f"/v1/sessions/{session}/tasks").json()["items"]
        assert all(row["question_source"]["filename"] == "questions.md" for row in public)
        again = upload(client, session, response_style="detailed")
        assert again.json()["id"] == identifier
        assert upload(client, session, response_style="brief").status_code == 409
        assert len(store.list_tasks(session, 10)[0]) == 2
        assert client.get(f"/v1/sessions/{foreign}/question-batches/{identifier}").status_code == 404
        page = client.get(f"/v1/sessions/{session}/question-batches?limit=1")
        assert page.headers["cache-control"] == "no-store" and "questions" not in page.json()["items"][0]
        assert "storage_key" not in json.dumps(item)
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), question_dir=tmp_path, rate_limits=False)) as client:
        restored = client.get(f"/v1/sessions/{session}/question-batches/{identifier}").json()
        assert restored == item


@pytest.mark.parametrize("kwargs,code", [
    ({"filename": "bad.txt"}, 415), ({"mime": "text/plain"}, 400),
    ({"content": b""}, 400), ({"content": b"not pdf", "filename": "bad.pdf", "mime": "application/pdf"}, 400),
    ({"response_style": "unknown"}, 400), ({"document_ids": "not json"}, 400),
    ({"document_ids": "null"}, 400), ({"document_ids": '["bad"]'}, 400),
    ({"document_ids": json.dumps([str(uuid4())] * 101)}, 400),
    ({"document_ids": json.dumps([str(uuid4())])}, 503),
])
def test_invalid_upload_or_options(tmp_path, kwargs, code):
    with TestClient(create_app(runtime=FakeRuntime(0), question_dir=tmp_path, rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        assert upload(client, session, **kwargs).status_code == code
        assert client.get(f"/v1/sessions/{session}/question-batches").json()["items"] == []


def test_rejected_structure_creates_no_tasks_and_cancel_stops_dispatch(tmp_path):
    with TestClient(create_app(runtime=FakeRuntime(.25), question_dir=tmp_path, rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        bad = upload(client, session, "## Topic A\nText.\n## Topic B\nText.").json()
        assert wait_batch(client, session, bad["id"], "failed")["error_code"] == "ambiguous_question_structure"
        assert client.get(f"/v1/sessions/{session}/tasks").json()["items"] == []
        item = upload(client, session).json()
        endpoint = f"/v1/sessions/{session}/question-batches/{item['id']}"
        start_batch(client, session, item["id"])
        wait_batch(client, session, item["id"], "solving")
        assert upload(client, session, TEXT + "extra").status_code == 409
        assert client.post(endpoint + "/cancel").status_code == 200
        assert client.post(endpoint + "/cancel").status_code == 200
        time.sleep(.6)
        result = client.get(endpoint).json()
        assert result["status"] == "cancelled" and result["counts"]["cancelled"] == 2
        assert client.post(endpoint + "/questions/1/retry").status_code == 409


def test_catalog_pages_owner_lock_and_scope(tmp_path):
    catalog = QuestionCatalog(tmp_path / "catalog.sqlite")
    from agent_platform.models import utc_now
    session, foreign = str(uuid4()), str(uuid4())
    for index in range(3):
        item = {"id": str(uuid4()), "session_id": session, "content_hash": str(index), "status": "completed", "created_at": utc_now().isoformat()}
        catalog.create(item)
    first, cursor = catalog.page(session, 1)
    second, following = catalog.page(session, 1, cursor)
    assert first[0]["id"] != second[0]["id"] and following
    with pytest.raises(PlatformError, match="invalid_cursor"):
        catalog.page(foreign, 1, cursor)
    catalog.close()


def test_disabled_capability_and_reserved_source():
    with TestClient(create_app(runtime=FakeRuntime(0), rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        assert client.get("/health/ready").json()["question_attachments"] is False
        assert upload(client, session).status_code == 503
        assert client.post(f"/v1/sessions/{session}/question-batches/{uuid4()}/start", json={"prompt": "Explain."}).status_code == 503
        response = client.post(f"/v1/sessions/{session}/tasks", json={"problem": "fixture", "metadata": {SOURCE_KEY: {"batch_id": str(uuid4())}}})
        assert response.status_code == 400


def test_failed_question_can_retry_without_replaying_other_questions(tmp_path):
    class FailOnce(FakeRuntime):
        def __init__(self):
            super().__init__(0)
            self.calls = 0
        async def run(self, context):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("synthetic failure")
            return await super().run(context)
    with TestClient(create_app(runtime=FailOnce(), question_dir=tmp_path, rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        item = upload(client, session).json()
        endpoint = f"/v1/sessions/{session}/question-batches/{item['id']}"
        start_batch(client, session, item["id"])
        value = wait_batch(client, session, item["id"])
        assert value["counts"]["failed"] == value["counts"]["succeeded"] == 1
        original = [question["task"]["id"] for question in value["questions"]]
        assert client.post(endpoint + "/questions/2/retry").status_code == 409
        assert client.post(endpoint + "/questions/0/retry").status_code == 409
        assert client.post(endpoint + "/questions/1/retry").status_code == 202
        value = wait_batch(client, session, item["id"])
        assert value["counts"]["succeeded"] == 2
        assert value["questions"][0]["task"]["id"] != original[0]
        assert client.app.state.store.get_task(session, value["questions"][0]["task"]["id"]).metadata[INSTRUCTION_KEY] == "Explain the solution."
        assert value["questions"][1]["task"]["id"] == original[1]
        assert client.post(endpoint + "/cancel").status_code == 409


def test_cancel_recovers_accepted_task_missing_catalog_acknowledgement(tmp_path):
    store = InMemoryTaskStore()
    app = create_app(store=store, runtime=FakeRuntime(1), question_dir=tmp_path, rate_limits=False)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        value = upload(client, session).json()
        endpoint = f"/v1/sessions/{session}/question-batches/{value['id']}"
        start_batch(client, session, value["id"])
        end = time.monotonic() + 10
        while time.monotonic() < end:
            item = client.get(endpoint).json()
            if item["questions"] and item["questions"][0]["task"]:
                break
            time.sleep(.05)
        task_id = item["questions"][0]["task"]["id"]
        internal = app.state.questions.catalog.get(session, value["id"])
        internal["questions"][0]["task_id"] = None
        app.state.questions.catalog.save(internal)
        assert client.post(endpoint + "/cancel").status_code == 200
        time.sleep(.2)
        assert store.get_task(session, task_id).cancellation_requested
        assert len(store.list_tasks(session, 20)[0]) == 1


def test_cancel_during_parsing_does_not_start_model_tasks(tmp_path):
    app = create_app(runtime=FakeRuntime(0), question_dir=tmp_path, rate_limits=False)
    async def delayed(*args, **kwargs):
        await asyncio.sleep(.5)
        return split_questions([TEXT])
    app.state.questions.parser = delayed
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        value = upload(client, session).json()
        assert client.post(f"/v1/sessions/{session}/question-batches/{value['id']}/cancel").status_code == 200
        time.sleep(.8)
        assert client.get(f"/v1/sessions/{session}/tasks").json()["items"] == []


def test_question_routes_reject_unscoped_invalid_requests(tmp_path):
    with TestClient(create_app(runtime=FakeRuntime(0), question_dir=tmp_path, rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        route = f"/v1/sessions/{session}/question-batches"
        assert client.post(route, data={"response_style": "auto"}).status_code == 400
        assert upload(client, session, unknown="value").status_code == 400
        assert client.get(route + "?limit=11").status_code == 400
        assert client.get(route + "?cursor=invalid").status_code == 400
        assert client.get(route + "/missing").status_code == 404
        assert upload(client, "missing").status_code == 404
        response = client.post(route, content=b"x", headers={"Content-Length": str(21 * 1024 * 1024)})
        assert response.status_code == 413


def test_reopen_recovers_lost_task_ack_without_resubmitting_work(tmp_path):
    from agent_platform.question_batches import QuestionBatchService
    from agent_platform.service import TaskService
    from starlette.datastructures import Headers, UploadFile
    store = InMemoryTaskStore()
    session = store.create_session(100).id
    tasks = TaskService(store, FakeRuntime(0))
    tasks.accepting = True
    async def parser(*args, **kwargs):
        return split_questions([TEXT])
    async def run():
        service = QuestionBatchService(tmp_path, tasks, parser=parser)
        service.accepting = True
        file = UploadFile(io.BytesIO(TEXT.encode()), filename="questions.md", headers=Headers({"content-type": "text/markdown"}))
        item = await service.upload(session, file, {"response_style": "auto", "document_ids": []})
        await service._advance(item)
        item = service.catalog.get(session, item["id"])
        item = service.begin(session, item["id"], "Explain the solution.", "auto")
        await service._advance(item)
        item = service.catalog.get(session, item["id"])
        first_id = item["questions"][0]["task_id"]
        item["questions"][0]["task_id"] = None
        service.catalog.save(item)
        await service.stop()
        restored = QuestionBatchService(tmp_path, tasks, parser=parser)
        try:
            await restored._advance(restored.catalog.get(session, item["id"]))
            item = restored.catalog.get(session, item["id"])
            assert item["questions"][0]["task_id"] == first_id
            assert len(store.list_tasks(session, 20)[0]) == 1
            await restored._advance(item)
            assert len(store.list_tasks(session, 20)[0]) == 1
            task = store.start(session, first_id, 1200)
            store.finish(session, first_id, task.generation, TaskStatus.SUCCEEDED, "synthetic response")
            await restored._advance(item)
            assert len(store.list_tasks(session, 20)[0]) == 2
        finally:
            await restored.stop()
    asyncio.run(run())


def test_ready_batch_survives_restart_without_tasks_and_start_is_idempotent(tmp_path):
    store = InMemoryTaskStore()
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), question_dir=tmp_path, rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        identifier = upload(client, session).json()["id"]
        before = wait_batch(client, session, identifier, "ready")
        assert upload(client, session).json()["id"] == identifier
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), question_dir=tmp_path, rate_limits=False)) as client:
        route = f"/v1/sessions/{session}/question-batches/{identifier}"
        time.sleep(.6)
        assert client.get(route).json() == before
        assert store.list_tasks(session, 20)[0] == []
        body = {"prompt": "Use algebra, with detailed steps.", "response_style": "detailed"}
        for _ in range(3):
            assert client.post(route + "/start", json=body).status_code == 202
        result = wait_batch(client, session, identifier)
        assert client.post(route + "/start", json=body).json() == result
        for changed in [{**body, "prompt": "Another request."}, {**body, "response_style": "answer"}]:
            assert client.post(route + "/start", json=changed).status_code == 409
        assert len(store.list_tasks(session, 20)[0]) == 2


def test_start_accepts_full_unicode_limit_and_sanitizes_public_instruction(tmp_path):
    with TestClient(create_app(runtime=FakeRuntime(0), question_dir=tmp_path, rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        identifier = upload(client, session).json()["id"]
        instruction = "请" * 3950 + " password=fixture-value C:\\private\\file"
        started = start_batch(client, session, identifier, prompt=instruction)
        assert "fixture-value" not in started["user_instruction"] and "C:" not in started["user_instruction"]
        assert "[redacted]" in started["user_instruction"]
        result = wait_batch(client, session, identifier)
        assert result["counts"]["succeeded"] == 2


@pytest.mark.parametrize("body", [
    {"prompt": None}, {"prompt": "x" * 4001}, {"prompt": 1}, {"prompt": True},
    {"prompt": ["text"]}, {"prompt": "text", "response_style": "unknown"},
    {"prompt": "text", "extra": True},
])
def test_invalid_start_never_dispatches_tasks(tmp_path, body):
    with TestClient(create_app(runtime=FakeRuntime(0), question_dir=tmp_path, rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        identifier = upload(client, session).json()["id"]
        wait_batch(client, session, identifier, "ready")
        assert client.post(f"/v1/sessions/{session}/question-batches/{identifier}/start", json=body).status_code == 400
        assert client.get(f"/v1/sessions/{session}/tasks").json()["items"] == []


@pytest.mark.parametrize("body", [{}, {"prompt": ""}, {"prompt": " \n "}])
def test_explicit_attachment_only_start_uses_original_problem_without_instruction(tmp_path, body):
    store = InMemoryTaskStore()
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), question_dir=tmp_path, rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        identifier = upload(client, session).json()["id"]
        preview = wait_batch(client, session, identifier, "ready")
        assert store.list_tasks(session, 20)[0] == []
        route = f"/v1/sessions/{session}/question-batches/{identifier}/start"
        assert client.post(route, json=body).status_code == 202
        result = wait_batch(client, session, identifier)
        assert result["user_instruction"] == ""
        for row, before in zip(result["questions"], preview["questions"]):
            task = store.get_task(session, row["task"]["id"])
            assert task.problem == before["problem"]
            assert INSTRUCTION_KEY not in task.metadata
            assert task.metadata["document_ids"] == []
        assert client.post(route, json={"prompt": ""}).status_code == 202
        assert len(store.list_tasks(session, 20)[0]) == 2


def test_start_scope_parsing_cancel_and_reserved_instruction(tmp_path):
    app = create_app(runtime=FakeRuntime(0), question_dir=tmp_path, rate_limits=False)
    async def delayed(*args, **kwargs):
        await asyncio.sleep(.5)
        return split_questions([TEXT])
    app.state.questions.parser = delayed
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        foreign = client.post("/v1/sessions", json={}).json()["id"]
        identifier = upload(client, session).json()["id"]
        route = f"/v1/sessions/{session}/question-batches/{identifier}"
        body = {"prompt": "Explain."}
        assert client.post(route + "/start", json=body).json()["error"]["code"] == "question_not_ready"
        assert client.post(f"/v1/sessions/{foreign}/question-batches/{identifier}/start", json=body).status_code == 404
        wait_batch(client, session, identifier, "ready")
        assert client.post(route + "/cancel").status_code == 200
        assert client.post(route + "/start", json=body).status_code == 409
        assert client.post(f"/v1/sessions/{session}/tasks", json={"problem": "fixture", "metadata": {INSTRUCTION_KEY: "override"}}).status_code == 400
        assert client.get(f"/v1/sessions/{session}/tasks").json()["items"] == []


def test_start_service_and_catalog_capacity_guards(tmp_path):
    from agent_platform.question_batches import QuestionBatchService
    from agent_platform.service import TaskService
    service = QuestionBatchService(tmp_path, TaskService(InMemoryTaskStore(), FakeRuntime(0)))
    identifier, session = str(uuid4()), str(uuid4())
    service.catalog.create({"id": identifier, "session_id": session, "content_hash": "ready", "status": "ready", "created_at": "2026-10-07T00:00:00+00:00"})
    try:
        with pytest.raises(PlatformError, match="question_service_unavailable"):
            service.begin(session, identifier, "Explain.", "auto")
        service.accepting = True
        for prompt, style in [(None, "auto"), ("x" * 4001, "auto"), ("Explain.", "bad")]:
            with pytest.raises(PlatformError, match="invalid_request"):
                service.begin(session, identifier, prompt, style)
        active = {"id": str(uuid4()), "session_id": session, "content_hash": "active", "status": "parsing", "created_at": "2026-10-07T00:00:00+00:00"}
        service.catalog.create(active)
        with pytest.raises(PlatformError, match="question_batch_active"):
            service.begin(session, identifier, "Explain.", "auto")
        for index in range(15):
            service.catalog.create({**active, "id": str(uuid4()), "session_id": str(index), "content_hash": str(index)})
        with pytest.raises(PlatformError, match="question_capacity_exceeded"):
            service.begin(session, identifier, "Explain.", "auto")
    finally:
        asyncio.run(service.stop())


def test_cancel_does_not_touch_unrelated_idempotency_collision(tmp_path):
    from agent_platform.question_batches import QuestionBatchService
    from agent_platform.service import TaskService
    store = InMemoryTaskStore()
    session = store.create_session(0).id
    service = QuestionBatchService(tmp_path, TaskService(store, FakeRuntime(0)))
    identifier = str(uuid4())
    task, _ = store.create_task(session, "unrelated", {}, "fake", f"question:{identifier}:1:0")
    item = {"id": identifier, "session_id": session, "content_hash": "fixture", "status": "solving",
            "created_at": task.accepted_at.isoformat(), "questions": [{"number": 1, "attempt": 0, "task_id": None}]}
    service.catalog.create(item)
    try:
        service.cancel(session, identifier)
        assert store.get_task(session, task.id).status == TaskStatus.QUEUED
        assert service.catalog.get(session, identifier)["questions"][0]["task_id"] is None
    finally:
        asyncio.run(service.stop())


def test_batch_capacity_upload_boundaries_and_owner_lock(tmp_path, monkeypatch):
    from agent_platform.question_batches import QuestionBatchService
    from agent_platform.service import TaskService
    from agent_platform.rag.models import MAX_BYTES
    from starlette.datastructures import Headers, UploadFile
    store = InMemoryTaskStore()
    service = QuestionBatchService(tmp_path, TaskService(store, FakeRuntime(0)))
    async def run():
        try:
            with pytest.raises(OSError):
                QuestionBatchService(tmp_path, service.tasks)
            file = UploadFile(io.BytesIO(TEXT.encode()), filename="questions.md", headers=Headers({"content-type": "text/markdown"}))
            with pytest.raises(PlatformError, match="question_service_unavailable"):
                await service.upload("fixture", file, {})
            service.accepting = True
            from collections import namedtuple
            usage = namedtuple("usage", "total used free")
            with monkeypatch.context() as patch:
                patch.setattr("agent_platform.question_batches.shutil.disk_usage", lambda _: usage(100, 100, 0))
                with pytest.raises(PlatformError, match="storage_capacity_exceeded"):
                    await service.upload("fixture", file, {})
            large = UploadFile(io.BytesIO(b"x" * (MAX_BYTES + 1)), filename="large.md", headers=Headers({"content-type": "text/markdown"}))
            with pytest.raises(PlatformError, match="file_too_large"):
                await service.upload("fixture", large, {})
            assert not list(tmp_path.glob("*.upload"))
            for index in range(16):
                service.catalog.create({"id": str(uuid4()), "session_id": str(index), "content_hash": str(index),
                                        "status": "parsing", "created_at": "2026-10-07T00:00:00+00:00"})
            with pytest.raises(PlatformError, match="question_capacity_exceeded"):
                service.catalog.create({"session_id": "extra"})
        finally:
            await service.stop()
    asyncio.run(run())


def test_question_selected_references_are_scoped_and_not_indexed(tmp_path):
    from agent_platform.rag.service import DocumentService
    from test_platform_rag import TestEmbedding, document, parsed
    documents = DocumentService(tmp_path / "rag", TestEmbedding())
    store = InMemoryTaskStore()
    session = store.create_session(100).id
    ready = document(session)
    documents.catalog.reserve(ready)
    documents.index.ingest(ready, parsed())
    failed = document(session, text="failed fixture")
    documents.catalog.reserve(failed)
    documents.catalog.fail(failed, "indexing_failed")
    foreign = document()
    documents.catalog.reserve(foreign)
    with TestClient(create_app(store=store, runtime=FakeRuntime(0), documents=documents,
                              question_dir=tmp_path / "questions", rate_limits=False)) as client:
        assert upload(client, session, document_ids=json.dumps([failed.id])).status_code == 409
        assert upload(client, session, document_ids=json.dumps([foreign.id])).status_code == 404
        result = upload(client, session, document_ids=json.dumps([ready.id])).json()
        start_batch(client, session, result["id"])
        batch = wait_batch(client, session, result["id"])
        for question in batch["questions"]:
            assert store.get_task(session, question["task"]["id"]).metadata["document_ids"] == [ready.id]
        assert len(documents.list(session, 10)["items"]) == 2


def test_worker_retries_capacity_then_reports_invalid_tasks(tmp_path):
    from unittest.mock import AsyncMock
    from agent_platform.question_batches import QuestionBatchService
    from agent_platform.service import TaskService
    store = InMemoryTaskStore()
    session = store.create_session(0).id
    service = QuestionBatchService(tmp_path, TaskService(store, FakeRuntime(0)), poll_seconds=.01)
    item = {"id": str(uuid4()), "session_id": session, "content_hash": "fixture", "status": "solving",
            "created_at": "2026-10-07T00:00:00+00:00", "questions": []}
    service.catalog.create(item)
    service._advance = AsyncMock(side_effect=[PlatformError("queue_capacity_exceeded", 429),
                                             PlatformError("storage_unavailable", 503),
                                             PlatformError("idempotency_conflict", 409)])
    async def run():
        await service.start()
        try:
            for _ in range(100):
                if service.catalog.get(session, item["id"])["status"] == "failed":
                    break
                await asyncio.sleep(.01)
            assert service._advance.await_count == 3
            assert service.catalog.get(session, item["id"])["error_code"] == "idempotency_conflict"
        finally:
            await service.stop()
    asyncio.run(run())


def test_parser_rejects_text_limit_encoding_encryption_and_partial_pdf(tmp_path):
    from agent_platform.rag.models import MAX_TEXT
    from pypdf import PdfReader, PdfWriter
    from scripts.smoke_platform_m5 import pdf_file
    with pytest.raises(ParseRejected, match="text_limit"):
        split_questions(["x" * (MAX_TEXT + 1)])
    path = tmp_path / "invalid.md"
    path.write_bytes(b"\xff")
    with pytest.raises(ParseRejected, match="invalid_utf8"):
        parse_questions(path, "text/markdown")
    reader = PdfReader(pdf_file().file)
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    writer.add_blank_page(width=600, height=800)
    path = tmp_path / "partial.pdf"
    with path.open("wb") as output:
        writer.write(output)
    with pytest.raises(ParseRejected, match="incomplete_pdf_text"):
        parse_questions(path, "application/pdf")
    writer.encrypt("synthetic-fixture")
    with path.open("wb") as output:
        writer.write(output)
    with pytest.raises(ParseRejected, match="encrypted_pdf"):
        parse_questions(path, "application/pdf")


@pytest.mark.parametrize("failure", ["catalog", "unexpected", "cancelled"])
def test_worker_fault_recovery_and_cancel_reconciliation(tmp_path, failure):
    import sqlite3
    from unittest.mock import AsyncMock
    from agent_platform.question_batches import QuestionBatchService
    from agent_platform.service import TaskService
    store = InMemoryTaskStore()
    session = store.create_session(0).id
    service = QuestionBatchService(tmp_path, TaskService(store, FakeRuntime(0)), poll_seconds=.01)
    item = {"id": str(uuid4()), "session_id": session, "content_hash": "fixture", "status": "solving",
            "created_at": "2026-10-07T00:00:00+00:00", "questions": []}
    if failure == "cancelled":
        item["status"] = "cancelled"
    service.catalog.create(item)
    if failure == "catalog":
        async def advance(row):
            row.update(status="completed")
            service.catalog.save(row)
        service._advance = AsyncMock(side_effect=[sqlite3.OperationalError("fixture outage"), None])
        original = service._advance
        async def retry(row):
            if original.await_count < 1:
                await original(row)
            else:
                await advance(row)
        service._advance = retry
    elif failure == "unexpected":
        service._advance = AsyncMock(side_effect=RuntimeError("fixture fault"))
    async def run():
        await service.start()
        try:
            for _ in range(100):
                value = service.catalog.get(session, item["id"])
                if value["status"] != "solving" and (failure != "cancelled" or value.get("cancel_reconciled")):
                    break
                await asyncio.sleep(.01)
            assert value["status"] == {"catalog": "completed", "unexpected": "failed", "cancelled": "cancelled"}[failure]
            if failure == "unexpected":
                assert value["error_code"] == "question_processing_failed"
            assert store.list_tasks(session, 20)[0] == []
        finally:
            await service.stop()
    asyncio.run(run())
