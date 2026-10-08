import asyncio
import copy
import json
import os
import threading
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from agent_platform.models import PlatformError, TaskStatus, utc_now
from agent_platform.runtime import RuntimeContext
from agent_platform.storage import InMemoryTaskStore
from agent_platform.tools.local import LocalTools
from agent_platform.tools.registry import ToolRegistry, failure, stable_call_id, validated_result
from agent_platform.tools.schemas import ARGUMENTS, ToolInvocation, ToolResult, definitions
from agent_platform.tools.symbolic import PolicyRejected, calculate, parse


def context(store=None, task=None):
    events = []
    ctx = RuntimeContext(
        task.id if task else "task", task.session_id if task else "session", "Problem", {}, (), None,
        lambda *args: None, deadline_at=utc_now() + timedelta(seconds=1200),
        record=lambda stage, kind, data: events.append((kind, data)),
        tool_calls=task.tool_calls if task else None,
        commit_tool=(lambda call_id, entry, kind, data: store.tool_record(
            task.session_id, task.id, task.generation, call_id, entry, kind, data)) if store else None,
    )
    return ctx, events


def request(ctx, name="math_verify", args=None, timeout=30000, call_id="call"):
    return ToolInvocation(call_id=call_id, task_id=ctx.task_id, stage_id="tool", tool_name=name,
                          arguments=args or {"problem": "Problem", "candidate": "Proof",
                                             "checks": ["proof_obligations"]}, timeout_ms=timeout)


def successful():
    return {"status": "succeeded", "value": {"verdict": "uncertain", "findings": [],
                                               "counterexample": None, "checked_claims": []}}


def target(*outcomes):
    return Mock(invoke=AsyncMock(side_effect=list(outcomes)))


@pytest.mark.parametrize("name,args", [
    ("strategy_search", {"query": "x", "top_k": True}),
    ("strategy_search", {"query": "x", "top_k": 21}),
    ("strategy_search", {"query": "x", "unknown": "value"}),
    ("strategy_search", {"query": "x" * 4001}),
    ("sympy_calculate", {"expression": "x", "operation": "exec"}),
    ("sympy_calculate", {"expression": "x", "operation": "solve", "variables": []}),
    ("sympy_calculate", {"expression": "x", "operation": "simplify", "variables": ["x", "x"]}),
    ("sympy_calculate", {"expression": "x", "operation": "simplify", "variables": ["x.y"]}),
    ("math_verify", {"problem": "x", "candidate": "x", "checks": []}),
    ("document_search", {"query": "x", "session_id": "invalid"}),
])
def test_invalid_arguments_are_not_executed_or_retried(name, args):
    ctx, events = context()
    local = target()
    result = asyncio.run(ToolRegistry(local).invoke(request(ctx, name, args), ctx))
    assert result.error_code == "invalid_arguments"
    assert local.invoke.call_count == 0 and not ctx.tool_calls
    assert events[0][0] == "tool.rejected"


def test_unknown_scope_timeout_and_definition_contracts():
    ctx, _ = context()
    registry = ToolRegistry(target())
    assert asyncio.run(registry.invoke(request(ctx, "unknown"), ctx)).error_code == "unknown_tool"
    wrong = request(ctx).model_copy(update={"task_id": "other"})
    assert asyncio.run(registry.invoke(wrong, ctx)).error_code == "scope_violation"
    with pytest.raises(ValidationError):
        request(ctx, timeout=30001)
    with pytest.raises(ValidationError):
        request(ctx).model_copy(update={"stage_id": "other"}).model_validate({**request(ctx).model_dump(), "stage_id": "other"})
    assert {item["function"]["name"] for item in definitions()} == set(ARGUMENTS)
    with pytest.raises(ValueError):
        ToolRegistry(mcp_tools=("sympy_calculate",))


@pytest.mark.parametrize("code,retryable,count", [
    ("transport_error", True, 3), ("timeout", True, 3), ("policy_rejected", True, 1),
    ("invalid_arguments", True, 1), ("execution_error", True, 1), ("timeout", False, 1),
])
def test_only_declared_retryable_failures_have_three_attempts(code, retryable, count):
    ctx, events = context()
    remote = target(*[failure(code, retryable=retryable).model_dump()] * 3)
    registry = ToolRegistry(target(), mcp=remote, equivalent_fallback=False)
    result = asyncio.run(registry.invoke(request(ctx), ctx))
    assert result.status == "failed" and remote.invoke.call_count == count
    assert len(ctx.tool_calls["call"]["attempts"]) == count
    assert len({data["call_id"] for kind, data in events if kind == "tool.started"}) == 1
    assert ctx.tool_calls["call"]["result"]["retryable"] is False


def test_retry_success_and_exact_local_fallback():
    ctx, _ = context()
    remote = target(failure("transport_error", retryable=True).model_dump(), successful())
    local = target(successful())
    result = asyncio.run(ToolRegistry(local, mcp=remote).invoke(request(ctx), ctx))
    assert result.status == "succeeded" and local.invoke.call_count == 0
    assert remote.invoke.call_count == 2
    ctx, events = context()
    remote = target(*[RuntimeError("private transport details")] * 3)
    result = asyncio.run(ToolRegistry(local, mcp=remote).invoke(request(ctx), ctx))
    assert result.status == "fallback" and local.invoke.call_count == 1
    assert "private" not in json.dumps(events)
    assert ctx.tool_calls["call"]["fallback_started"]


@pytest.mark.parametrize("bad", [
    {"status": "succeeded", "value": {"verdict": "correct"}},
    {"status": "succeeded", "value": {"verdict": "pass", "findings": [], "checked_claims": [], "secret": "x"}},
    {"status": "succeeded", "value": {"verdict": "pass", "findings": ["x" * 66000], "checked_claims": []}},
    {"status": "failed"}, {"status": "succeeded", "error_code": "timeout", "value": {}},
])
def test_hostile_or_incoherent_results_fail_closed_without_retry(bad):
    ctx, _ = context()
    remote = target(bad)
    local = target(successful())
    result = asyncio.run(ToolRegistry(local, mcp=remote).invoke(request(ctx), ctx))
    assert result.error_code == "invalid_result"
    assert remote.invoke.call_count == 1 and local.invoke.call_count == 0


def test_result_secret_sanitization_and_nonfinite_scores():
    raw = successful()
    raw["value"]["findings"] = ["Bearer fixture_sensitive_value", r"C:\private\file"]
    assert "fixture_sensitive" not in validated_result("math_verify", raw).model_dump_json()
    bad = {"status": "succeeded", "value": {"matches": [{"strategy_id": "a", "title": "b", "summary": "c",
           "score": float("nan"), "source_version": "v1"}]}}
    with pytest.raises(ValueError):
        validated_result("strategy_search", bad)


def test_failure_fallback_and_budget_boundaries():
    ctx, _ = context()
    ctx.deadline_at = utc_now() + timedelta(seconds=26)
    remote = target(successful())
    assert asyncio.run(ToolRegistry(remote).invoke(request(ctx), ctx)).error_code == "budget_exhausted"
    assert remote.invoke.call_count == 0
    ctx, _ = context()
    for number in range(64):
        ctx.tool_calls[str(number)] = {}
    assert asyncio.run(ToolRegistry(remote).invoke(request(ctx), ctx)).error_code == "budget_exhausted"
    ctx, _ = context()
    remote = target(*[RuntimeError()] * 3)
    local = target(RuntimeError("private"))
    result = asyncio.run(ToolRegistry(local, mcp=remote).invoke(request(ctx), ctx))
    assert result.error_code == "execution_error"


def test_timeouts_retry_and_cancellation_wait_for_cleanup():
    async def run(cancel):
        ctx, _ = context()
        started, cleaned = asyncio.Event(), []
        async def slow(*args):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.append(True)
        remote = Mock(invoke=slow)
        registry = ToolRegistry(target(), mcp=remote, equivalent_fallback=False)
        work = asyncio.create_task(registry.invoke(request(ctx, timeout=20), ctx))
        await started.wait()
        if cancel:
            ctx.cancelled.set()
            with pytest.raises(asyncio.CancelledError):
                await work
            assert len(cleaned) == 1
        else:
            assert (await work).error_code == "retry_exhausted"
            assert len(cleaned) == 3
    asyncio.run(run(False))
    asyncio.run(run(True))


@pytest.mark.parametrize("redis", [False, True])
def test_durable_result_replay_and_interrupted_attempt_budget(redis):
    if redis:
        from agent_platform.redis_store import RedisTaskStore
        import fakeredis
        server = fakeredis.FakeServer()
        store = RedisTaskStore(fakeredis.FakeRedis(server=server, decode_responses=True), require_aof=False)
        def reloaded():
            return RedisTaskStore(fakeredis.FakeRedis(server=server, decode_responses=True), require_aof=False)
    else:
        store = InMemoryTaskStore()
        reloaded = lambda: store
    session = store.create_session(0)
    task, _ = store.create_task(session.id, "Problem", {}, "fixture", None)
    task = store.start(session.id, task.id, 1200)
    ctx, _ = context(store, task)
    local = target(successful())
    first = asyncio.run(ToolRegistry(local).invoke(request(ctx), ctx))
    store.finish(session.id, task.id, task.generation, TaskStatus.INTERRUPTED)
    store = reloaded()
    store.resume(session.id, task.id)
    task = store.start(session.id, task.id, 1200)
    restored, _ = context(store, task)
    replay = asyncio.run(ToolRegistry(local).invoke(request(restored), restored))
    assert first == replay and local.invoke.call_count == 1
    entry = copy.deepcopy(task.tool_calls["call"])
    entry.update(result=None, status="started")
    entry["attempts"] = [{"id": str(number), "attempt": number, "status": "started"} for number in range(3)]
    restored.tool_calls["call"] = entry
    assert asyncio.run(ToolRegistry(local, equivalent_fallback=False).invoke(request(restored), restored)).error_code == "retry_exhausted"
    assert local.invoke.call_count == 1
    wrong = request(restored, args={"problem": "Other", "candidate": "Proof", "checks": ["proof_obligations"]})
    assert asyncio.run(ToolRegistry(local).invoke(wrong, restored)).error_code == "idempotency_conflict"
    store.cancel(session.id, task.id)
    with pytest.raises(PlatformError):
        store.tool_record(session.id, task.id, task.generation, "call", entry, "tool.started", {})


def test_result_commits_atomically_with_completion_before_later_crash():
    ctx, _ = context()
    entries = {}
    def commit(call_id, entry, kind, payload):
        if kind == "tool.committed":
            raise RuntimeError("crash after completed result")
        entries[call_id] = copy.deepcopy(entry)
    ctx._commit_tool = commit
    local = target(successful())
    with pytest.raises(RuntimeError):
        asyncio.run(ToolRegistry(local).invoke(request(ctx), ctx))
    restored, _ = context()
    restored.tool_calls = entries
    assert asyncio.run(ToolRegistry(local).invoke(request(restored), restored)).status == "succeeded"
    assert local.invoke.call_count == 1


@pytest.mark.parametrize("expr", [
    "x.__class__", "x[0]", "'text'", "lambda:1", "[x for x in []]", "__import__('os')", "factorial(3)",
    "y+1", "True", "sin(x, x)", "Eq(x=1)", "x**101", "x**x", "x**(-101)", "0x10", "1j",
    "1" * 101, "1e999999", "x<1<2", "x+", "(" * 201, "+".join(["x"] * 80), "sin",
])
def test_symbolic_grammar_rejects_code_and_resource_abuse(expr):
    with pytest.raises(PolicyRejected):
        calculate({"expression": expr, "operation": "simplify", "variables": ["x"], "assumptions": []})


@pytest.mark.parametrize("expr,op,variables,want", [
    ("x+x", "simplify", ["x"], "2*x"), ("x**2-1", "solve", ["x"], "[-1, 1]"),
    ("x**2", "differentiate", ["x"], "2*x"), ("x", "integrate", ["x"], "x**2/2"),
    ("1/2", "numeric", [], "0.5"), ("-1+2*3/4", "simplify", [], "1/2"),
    ("+2%2", "simplify", [], "0"), (".5+1e-1", "simplify", [], "3/5"),
    ("Eq(1,1)", "simplify", [], "True"), ("1!=2", "simplify", [], "True"),
    ("1<2", "simplify", [], "True"), ("1<=2", "simplify", [], "True"),
    ("2>1", "simplify", [], "True"), ("2>=1", "simplify", [], "True"),
    ("sin(0)+cos(0)+tan(0)+exp(0)+log(1)+sqrt(4)+Abs(-1)", "simplify", [], "5"),
])
def test_symbolic_construction_and_operations(expr, op, variables, want):
    result = calculate({"expression": expr, "operation": op, "variables": variables, "assumptions": []})
    assert result["value"].startswith(want)


@pytest.mark.parametrize("name", ["sin", "Eq"])
def test_symbols_cannot_shadow_allowed_functions(name):
    with pytest.raises(PolicyRejected):
        calculate({"expression": name, "operation": "simplify", "variables": [name], "assumptions": []})


def test_actual_isolated_calculation_and_math_verification():
    async def run():
        local = LocalTools()
        result = await local.invoke("sympy_calculate", {"expression": "x**2", "operation": "differentiate", "variables": ["x"]})
        assert result["status"] == "succeeded" and result["value"]["value"] == "2*x"
        bad = await local.invoke("sympy_calculate", {"expression": "x.__class__", "operation": "simplify", "variables": ["x"]})
        assert bad["error_code"] == "policy_rejected"
        verified = await local.invoke("math_verify", {"problem": "Calculate", "candidate": "$1+1=3$",
                                                      "checks": ["numeric_equivalence"]})
        assert verified["value"]["verdict"] == "fail"
        ok = await local.invoke("math_verify", {"problem": "Calculate", "candidate": "$1+1=2$",
                                                "checks": ["numeric_equivalence", "proof_obligations"]})
        assert ok["value"]["verdict"] == "uncertain" and ok["value"]["checked_claims"] == ["1+1==2"]
    asyncio.run(run())


def test_document_interface_is_unavailable_and_session_scoped():
    ctx, events = context()
    ctx.session_id = "00000000-0000-0000-0000-000000000001"
    args = {"query": "Evidence", "session_id": ctx.session_id}
    registry = ToolRegistry()
    result = asyncio.run(registry.invoke(request(ctx, "document_search", args), ctx))
    assert result.error_code == "unavailable" and not result.value
    args["session_id"] = "00000000-0000-0000-0000-000000000002"
    assert asyncio.run(registry.invoke(request(ctx, "document_search", args), ctx)).error_code == "scope_violation"
    assert stable_call_id(ctx, "tool", 0, "document_search", args) == stable_call_id(ctx, "tool", 0, "document_search", args)


def test_local_search_versioned_bounded_results_and_no_raw_sources():
    retriever = Mock()
    retriever.retrieve_for_structure.return_value = {"index_version": "fixture-v1", "results": [
        {"id": "method-1", "name": "Method", "description": "x" * 3000, "steps": [], "score": .5,
         "raw_response": "private"}]}
    result = asyncio.run(LocalTools(retriever).invoke("strategy_search", {"query": "Method"}))
    validated = validated_result("strategy_search", result)
    assert len(validated.value["matches"][0]["summary"]) <= 2000
    assert "private" not in validated.model_dump_json()


@pytest.mark.skipif(os.name != "nt", reason="Windows job limits")
def test_windows_job_enforces_real_memory_cpu_and_tree_cleanup():
    import subprocess
    import sys
    import win32job
    from agent_platform.tools.isolation import windows_job
    process = subprocess.Popen([sys.executable, "-c", "import sys;sys.stdin.readline()"], stdin=subprocess.PIPE)
    try:
        job = windows_job(process.pid)
        limits = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
        assert limits["ProcessMemoryLimit"] == 256 * 1024 * 1024
        assert limits["BasicLimitInformation"]["PerProcessUserTimeLimit"] == 50000000
        job.Close()
        # Windows may use exit code zero for job termination; completion while
        # stdin is still open proves the blocked worker was killed.
        process.wait(timeout=5)
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdin.close()


def test_local_verifier_limits_are_uncertain_not_success():
    async def run():
        local = LocalTools(concurrency=1)
        local.permits.acquire()
        work = asyncio.create_task(local.invoke("math_verify", {"problem": "p", "candidate": "$1+1=2$",
                                                                "checks": ["numeric_equivalence"]}))
        await asyncio.sleep(.03)
        local.permits.release()
        with patch("agent_platform.tools.local.isolated_calculate", AsyncMock(return_value={"status": "failed"})):
            result = await work
        assert result["value"]["verdict"] == "uncertain" and not result["value"]["checked_claims"]
        with patch("agent_platform.tools.local.isolated_calculate", AsyncMock(return_value={"status": "succeeded", "value": {"value": "not_boolean"}})):
            result = await local.invoke("math_verify", {"problem": "p", "candidate": "$1+1=2$", "checks": ["numeric_equivalence"]})
        assert not result["value"]["checked_claims"]
    asyncio.run(run())


def test_context_refuses_tool_commits_after_cancellation():
    ctx, _ = context()
    ctx.cancelled.set()
    with pytest.raises(RuntimeError):
        ctx.commit_tool("call", {}, "tool.started", {})
    store = InMemoryTaskStore()
    session = store.create_session(0)
    task, _ = store.create_task(session.id, "Problem", {}, "fixture", None)
    task = store.start(session.id, task.id, 1200)
    entry = {"stage_id": "tool", "arguments_hash": "0" * 64, "result": None,
             "attempts": [{"status": "started"}, {"status": "failed"}]}
    store.tool_record(session.id, task.id, task.generation, "call", entry, "tool.started", {"operation_id": "attempt"})
    finished = store.finish(session.id, task.id, task.generation, TaskStatus.INTERRUPTED)
    assert finished.tool_calls["call"]["status"] == "interrupted"
    assert finished.tool_calls["call"]["attempts"][0]["status"] == "interrupted"
    assert finished.tool_calls["call"]["attempts"][1]["status"] == "failed"


def test_concurrent_duplicate_call_id_executes_once():
    async def run():
        ctx, events = context()
        async def slow(*args):
            await asyncio.sleep(.03)
            return successful()
        local = Mock(invoke=AsyncMock(side_effect=slow))
        registry = ToolRegistry(local)
        results = await asyncio.gather(registry.invoke(request(ctx), ctx), registry.invoke(request(ctx), ctx))
        assert results[0] == results[1] and local.invoke.call_count == 1
        assert sum(kind == "tool.started" for kind, _ in events) == 1
        assert sum(kind == "tool.replayed" for kind, _ in events) == 1
        ctx.tool_locks = {str(number): threading.Lock() for number in range(64)}
        assert (await registry.invoke(request(ctx), ctx)).error_code == "budget_exhausted"
    asyncio.run(run())


def test_tool_results_and_ids_are_isolated_across_100_session_pairs():
    store = InMemoryTaskStore()
    async def invoke(name, arguments):
        result = successful()
        result["value"]["checked_claims"] = [arguments["candidate"]]
        return result
    registry = ToolRegistry(Mock(invoke=AsyncMock(side_effect=invoke)))
    for number in range(100):
        tasks = []
        for side in ("left", "right"):
            session = store.create_session(0)
            task, _ = store.create_task(session.id, "Problem", {}, "fixture", None)
            task = store.start(session.id, task.id, 1200)
            ctx, _ = context(store, task)
            marker = f"session-{number}-{side}"
            args = {"problem": "Problem", "candidate": marker, "checks": ["proof_obligations"]}
            asyncio.run(registry.invoke(request(ctx, args=args, call_id="same-client-id"), ctx))
            tasks.append((task, marker))
        for task, marker in tasks:
            persisted = store.get_task(task.session_id, task.id)
            assert persisted.tool_calls["same-client-id"]["result"]["value"]["checked_claims"] == [marker]
            assert all(event.session_id == task.session_id and event.task_id == task.id for event in persisted.events)
            other = tasks[1] if task == tasks[0][0] else tasks[0]
            with pytest.raises(PlatformError):
                store.get_task(task.session_id, other[0].id)
