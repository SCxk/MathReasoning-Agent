import asyncio
import copy
import json
import threading
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

import pytest

pytest.importorskip("langgraph")

from agent_platform.graph_runtime import LangGraphRuntime, route
from agent_platform.models import Message, TaskStatus, utc_now
from agent_platform.runtime import CheckpointIncompatible, RuntimeContext
from agent_platform.service import TaskService
from agent_platform.staged_adapter import ExecutionStopped, StagedAdapter, TracedClient
from agent_platform.storage import InMemoryTaskStore
from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom2.staged_models import StagedAudit, StagedModelFidelity


def draft(value="2", *, proof=False):
    return (
        "## 问题分析\nUse the given definition.\n"
        "## 详细解题步骤\nThe defining calculation gives the result.\n"
        f"## 最终答案\n{value if proof else chr(92) + 'boxed{' + value + '}'}\n"
        "## 关键验证点\nCheck the defining condition."
    )


class ScriptedClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, temperature, max_tokens, request_timeout=None, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def config(**updates):
    return replace(AgentConfig(custom2_solver_protocol="staged"),
                   staged_strategy_retrieval_enabled=False,
                   staged_strategy_model_enabled=True,
                   staged_compact_reasoning_only=False,
                   staged_solver_compressed_retry_enabled=False, **updates)


def client_for_pass(*, proof=False):
    return ScriptedClient([
        json.dumps({"answer_mode": "proof" if proof else "computation", "domain": "linear_algebra"}),
        '{"risk_level":"high"}', draft("Conclusion follows." if proof else "2", proof=proof),
        '{"verdict":"pass"}', '{"verdict":"pass"}',
    ])


def context(checkpoint=None, deadline=None):
    events, checkpoints = [], []
    ctx = RuntimeContext("task", "session", "Compute a value from its definition.", {}, (), checkpoint,
                         lambda stage, completed, state: checkpoints.append(copy.deepcopy(state)) if completed else None,
                         deadline_at=deadline or utc_now() + timedelta(seconds=1200),
                         record=lambda stage, kind, data: events.append((stage, kind, data)))
    return ctx, events, checkpoints


@pytest.mark.parametrize("proof", [False, True])
def test_real_stage_adapter_uses_injected_client_and_serializable_checkpoints(proof):
    client = client_for_pass(proof=proof)
    runtime = LangGraphRuntime(client, config())
    ctx, events, checkpoints = context()
    if proof:
        ctx.problem = "Prove the stated conclusion from the definition."
    result = asyncio.run(runtime.run(ctx))
    assert len(client.calls) == 5
    assert ("## 详细解题步骤" in result.final_response) if proof else result.final_response == r"\boxed{2}"
    assert [state["next_stage"] for state in checkpoints] == [
        "retrieve", "plan", "solve", "tool", "verify", "finalize", "terminal",
    ]
    assert sum(kind == "model.started" for _, kind, _ in events) == 5
    assert sum(kind == "model.completed" for _, kind, _ in events) == 5
    assert "messages" not in json.dumps(events) and "raw_response" not in json.dumps(checkpoints)
    json.dumps(checkpoints, allow_nan=False)


def test_resume_at_every_completed_node_does_not_replay_model_calls():
    runtime = LangGraphRuntime(client_for_pass(), config())
    ctx, _, checkpoints = context()
    asyncio.run(runtime.run(ctx))
    expected = [4, 4, 3, 2, 2, 0, 0]
    remaining = [
        ['{"risk_level":"high"}', draft(), '{"verdict":"pass"}', '{"verdict":"pass"}'],
        ['{"risk_level":"high"}', draft(), '{"verdict":"pass"}', '{"verdict":"pass"}'],
        [draft(), '{"verdict":"pass"}', '{"verdict":"pass"}'],
        ['{"verdict":"pass"}', '{"verdict":"pass"}'],
        ['{"verdict":"pass"}', '{"verdict":"pass"}'], [], [],
    ]
    for checkpoint, count, responses in zip(checkpoints, expected, remaining):
        client = ScriptedClient(responses)
        resumed = LangGraphRuntime(client, config())
        new, _, completed = context(checkpoint, ctx.deadline_at)
        assert asyncio.run(resumed.run(new)).final_response == r"\boxed{2}"
        assert len(client.calls) == count


@pytest.mark.parametrize("change", ["version", "owner", "problem", "config", "deadline", "next_stage"])
def test_checkpoint_mismatch_is_rejected(change):
    runtime = LangGraphRuntime(client_for_pass(), config())
    ctx, _, checkpoints = context()
    asyncio.run(runtime.run(ctx))
    state = checkpoints[-1]
    state[{"version": "schema_version", "owner": "session_id", "problem": "problem_hash",
           "config": "config_hash", "deadline": "deadline_at", "next_stage": "next_stage"}[change]] = "bad"
    resumed, _, _ = context(state, ctx.deadline_at)
    with pytest.raises(CheckpointIncompatible):
        asyncio.run(runtime.run(resumed))


@pytest.mark.parametrize("verdict,evidence,count,solve,budget,want", [
    ("pass", "", 0, 1, True, "finalize"),
    ("uncertain", "", 0, 1, True, "finalize"),
    ("fail", "", 0, 1, True, "finalize"),
    ("fail", "quoted defect", 0, 1, True, "repair"),
    ("fail", "quoted defect", 3, 4, True, "finalize"),
    ("fail", "quoted defect", 0, 4, True, "finalize"),
    ("fail", "quoted defect", 0, 1, False, "finalize"),
])
def test_verification_routing(verdict, evidence, count, solve, budget, want):
    state = {"verification": {"verdict": verdict, "first_fatal_error": evidence},
             "repair_count": count, "max_repairs": 3, "solve_calls_used": solve, "max_solve_calls": 4}
    assert route("verify", state, budget_available=budget) == want


@pytest.mark.parametrize("repair_pass", [False, True])
def test_repair_replaces_candidate_only_after_pass(repair_pass):
    client = ScriptedClient(['{"answer_mode":"computation"}', '{"risk_level":"high"}', draft("3"), draft("7")])
    reviews = [StagedAudit(verdict="fail", first_fatal_error="wrong step"),
               StagedAudit(verdict="pass" if repair_pass else "fail", first_fatal_error="still wrong")]
    runtime = LangGraphRuntime(client, config(custom2_max_repairs=1))
    ctx, _, checkpoints = context()
    with patch.object(StagedAdapter, "_model_fidelity", return_value=StagedModelFidelity(verdict="pass")), \
         patch.object(StagedAdapter, "_audit", side_effect=reviews):
        result = asyncio.run(runtime.run(ctx))
    assert result.final_response == (r"\boxed{7}" if repair_pass else r"\boxed{3}")
    assert checkpoints[-1]["repair_count"] == 1
    assert checkpoints[-1]["solve_calls_used"] == 2


def test_tool_failure_does_not_erase_candidate():
    runtime = LangGraphRuntime(client_for_pass(), config(custom2_max_repairs=0))
    ctx, events, checkpoints = context()
    with patch.object(StagedAdapter, "_local_checks", side_effect=RuntimeError("private failure")):
        result = asyncio.run(runtime.run(ctx))
    assert result.final_response == r"\boxed{2}"
    assert any(kind == "candidate_check.failed" for _, kind, _ in events)
    assert checkpoints[-1]["adapter"]["_best_candidate_draft"]
    assert "private failure" not in json.dumps(events)


def test_typed_tool_execution_failure_preserves_saved_candidate():
    runtime = LangGraphRuntime(client_for_pass(), config(custom2_max_repairs=0))
    ctx, events, checkpoints = context()
    with patch("agent_platform.tools.local.LocalTools.math_verify", side_effect=RuntimeError("private tool failure")):
        result = asyncio.run(runtime.run(ctx))
    assert result.final_response == r"\boxed{2}"
    assert any(kind == "tool.failed" for _, kind, _ in events)
    assert checkpoints[-1]["adapter"]["_best_candidate_draft"]
    assert "private tool failure" not in json.dumps(events)


def test_cancel_during_typed_tool_kills_work_without_losing_checkpoint_candidate():
    from unittest.mock import Mock
    from agent_platform.tools.registry import ToolRegistry
    async def run():
        started, cleaned = threading.Event(), threading.Event()
        async def slow(name, arguments):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        runtime = LangGraphRuntime(client_for_pass(), config(), tools=ToolRegistry(Mock(invoke=slow)))
        ctx, events, checkpoints = context()
        work = asyncio.create_task(runtime.run(ctx))
        assert await asyncio.to_thread(started.wait, 2)
        ctx.cancelled.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(work, 2)
        assert await asyncio.to_thread(cleaned.wait, 2)
        assert checkpoints[-1]["next_stage"] == "tool" and ctx.saved_response == r"\boxed{2}"
        assert not any(kind == "tool.completed" for _, kind, _ in events)
        assert len(runtime.client.calls) == 3
    asyncio.run(run())


def test_unhandled_verify_failure_returns_saved_candidate():
    runtime = LangGraphRuntime(client_for_pass(), config())
    ctx, events, _ = context()
    with patch.object(StagedAdapter, "_model_fidelity", side_effect=RuntimeError("private")):
        assert asyncio.run(runtime.run(ctx)).final_response == r"\boxed{2}"
    assert any(kind == "stage.recovered_error" for _, kind, _ in events)


def test_finalization_budget_and_failed_solve_never_fabricate_answer():
    runtime = LangGraphRuntime(ScriptedClient([]), config())
    ctx, _, _ = context(deadline=utc_now() + timedelta(seconds=20))
    with pytest.raises(ValueError):
        asyncio.run(runtime.run(ctx))
    runtime = LangGraphRuntime(ScriptedClient(['{}', '{"risk_level":"high"}', '']), config())
    ctx, _, _ = context()
    with pytest.raises(ValueError):
        asyncio.run(runtime.run(ctx))


def test_model_failure_trace_no_secret_and_minimal_client_signature():
    class Minimal:
        def chat(self, messages, temperature, max_tokens):
            return {"content": "ok", "usage": {"total_tokens": 3, "raw": "private"}}
    ctx, events, _ = context()
    proxy = TracedClient(Minimal(), ctx, "solve", threading.BoundedSemaphore(1))
    assert proxy.chat(messages=[], temperature=0, max_tokens=10, request_timeout=1)["content"] == "ok"
    assert events[-1][2]["usage"] == {"total_tokens": 3}
    failure = TracedClient(ScriptedClient([RuntimeError("secret=private")]), ctx, "solve", threading.BoundedSemaphore(1))
    with pytest.raises(RuntimeError):
        failure.chat(messages=[], temperature=0, max_tokens=10, request_timeout=1)
    assert events[-1][1] == "model.failed"
    assert "secret=" not in json.dumps(events)


def test_cancellation_holds_model_permit_and_discards_late_results():
    entered, release = threading.Event(), threading.Event()
    class Blocking:
        def chat(self, **kwargs):
            entered.set()
            release.wait(2)
            return "late"
    ctx, events, _ = context()
    permits = threading.BoundedSemaphore(1)
    proxy = TracedClient(Blocking(), ctx, "solve", permits)
    errors = []
    def invoke():
        try:
            proxy.chat(request_timeout=1)
        except ExecutionStopped:
            errors.append("stopped")
    thread = threading.Thread(target=invoke)
    thread.start()
    assert entered.wait(1)
    ctx.cancelled.set()
    assert not permits.acquire(blocking=False)
    release.set()
    thread.join(2)
    assert errors == ["stopped"]
    assert permits.acquire(blocking=False)
    assert [event[1] for event in events] == ["model.started"]


def test_session_memory_is_advisory_and_official_entrypoint_remains_independent():
    runtime = LangGraphRuntime(client_for_pass(), config())
    ctx, _, _ = context()
    ctx.memory = (Message("message", "user", "previous context", "old-task"),)
    asyncio.run(runtime.run(ctx))
    solver = runtime.client.calls[2]["messages"]
    assert "previous context" in solver[0]["content"]
    assert ctx.problem in solver[1]["content"]
    assert "previous context" not in json.dumps(runtime.client.calls[0])


def test_service_keeps_incompatible_task_interrupted():
    async def check():
        store = InMemoryTaskStore()
        session = store.create_session(0)
        task, _ = store.create_task(session.id, "test", {}, "langgraph_staged", None)
        started = store.start(session.id, task.id, 1200)
        store.progress(session.id, task.id, started.generation, "profile", True, {"schema_version": "bad"})
        store.finish(session.id, task.id, started.generation, TaskStatus.INTERRUPTED)
        service = TaskService(store, LangGraphRuntime(ScriptedClient([]), config()))
        await service.start()
        service.resume(session.id, task.id)
        for _ in range(100):
            await asyncio.sleep(.01)
            final = store.get_task(session.id, task.id)
            if final.status == TaskStatus.INTERRUPTED:
                break
        await service.stop()
        assert final.error_code == "checkpoint_incompatible"
    asyncio.run(check())


def test_configuration_validation_and_direct_context_deadline():
    with pytest.raises(ValueError, match="injected_client_required"):
        LangGraphRuntime(None)
    with pytest.raises(ValueError, match="invalid_model_concurrency"):
        LangGraphRuntime(client_for_pass(), model_concurrency=0)
    runtime = LangGraphRuntime(client_for_pass(), config())
    ctx, _, _ = context()
    ctx.deadline_at = None
    assert asyncio.run(runtime.run(ctx)).final_response
    with pytest.raises(ValueError, match="invalid_recovery_configuration"):
        TaskService(InMemoryTaskStore(), runtime, recovery_poll_seconds=0)
    ctx, _, _ = context()
    ctx.finalize_reserve_seconds = 0
    with pytest.raises(ValueError, match="graph_requires_finalize_reserve"):
        asyncio.run(runtime.run(ctx))
    assert runtime.checkpoint_compatible(None)
    ctx = RuntimeContext("task", "session", "input", {}, (), None, lambda *args: None)
    ctx.record("solve", "model.completed", {})
    ctx.cancelled.set()
    with pytest.raises(RuntimeError, match="execution_stopped"):
        ctx.record("solve", "model.completed", {})


def test_corrupt_checkpoint_fields_fail_closed():
    runtime = LangGraphRuntime(client_for_pass(), config())
    ctx, _, states = context()
    asyncio.run(runtime.run(ctx))
    for index, remove in [(0, "profile"), (2, "plan"), (3, "draft"), (4, "checks"), (6, "final_response")]:
        state = copy.deepcopy(states[index])
        state.pop(remove)
        assert not runtime.checkpoint_compatible(state)
    state = copy.deepcopy(states[0])
    state["deadline_at"] = "2026-10-04T00:00:00"
    assert not runtime.checkpoint_compatible(state)
    state["deadline_at"] = "not-a-date"
    assert not runtime.checkpoint_compatible(state)
    state = copy.deepcopy(states[4])
    state["next_stage"] = "repair"
    state.pop("verification", None)
    assert not runtime.checkpoint_compatible(state)


def test_graph_cancellation_before_and_during_node():
    runtime = LangGraphRuntime(client_for_pass(), config())
    ctx, _, _ = context()
    ctx.cancelled.set()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(runtime.run(ctx))
    ctx, _, _ = context()
    with patch.object(StagedAdapter, "execute", side_effect=ExecutionStopped()), \
         pytest.raises(asyncio.CancelledError):
        asyncio.run(runtime.run(ctx))


def test_model_concurrency_cap_across_task_contexts():
    from concurrent.futures import ThreadPoolExecutor
    import time

    lock = threading.Lock()
    active = maximum = 0
    class Client:
        def chat(self, **kwargs):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(.01)
            with lock:
                active -= 1
            return "ok"
    permits = threading.BoundedSemaphore(2)
    def call(_):
        ctx, _, _ = context()
        return TracedClient(Client(), ctx, "solve", permits).chat(request_timeout=2)
    with ThreadPoolExecutor(12) as pool:
        assert list(pool.map(call, range(20))) == ["ok"] * 20
    assert maximum == 2


def test_solver_started_budget_is_enforced_before_client_invocation():
    ctx, events, _ = context()
    ctx.max_solve_calls = 1
    ctx.solver_calls_used = 1
    client = ScriptedClient(["never used"])
    proxy = TracedClient(client, ctx, "solve", threading.BoundedSemaphore(1))
    proxy.call_type = "solver"
    from reasoning_agent.custom2.model_call import ModelCallBudgetExhausted
    with pytest.raises(ModelCallBudgetExhausted):
        proxy.chat(request_timeout=1)
    assert not client.calls and events[-1][1] == "model.budget_exhausted"


def test_model_permit_wait_deadline_and_cancel():
    ctx, _, _ = context()
    permits = threading.BoundedSemaphore(1)
    permits.acquire()
    proxy = TracedClient(client_for_pass(), ctx, "profile", permits)
    with pytest.raises(TimeoutError, match="model_capacity_deadline"):
        proxy.chat(request_timeout=.001)
    ctx.cancelled.set()
    with pytest.raises(ExecutionStopped):
        proxy.chat(request_timeout=1)
    permits.release()


def test_large_candidate_rejection_and_partial_candidate_acceptance():
    runtime = LangGraphRuntime(client_for_pass(), config())
    for response, ok in [(None, True), ("x" * 48001, False)]:
        ctx, _, _ = context()
        with patch.object(StagedAdapter, "_solve", return_value=response), \
             patch.object(StagedAdapter, "_last_solver_partial", draft(), create=True):
            # Constructor resets this value, so set the partial on invocation.
            def solve(adapter, *args, **kwargs):
                adapter._last_solver_partial = draft()
                return response
            with patch.object(StagedAdapter, "_solve", solve):
                if ok:
                    fresh = LangGraphRuntime(client_for_pass(), config())
                    assert asyncio.run(fresh.run(ctx)).final_response
                else:
                    with pytest.raises(ValueError):
                        asyncio.run(LangGraphRuntime(client_for_pass(), config()).run(ctx))


def test_low_risk_verification_and_skill_material_fallback():
    runtime = LangGraphRuntime(ScriptedClient(['{}', '{"risk_level":"low"}', draft(),
                                              '{"verdict":"pass"}', '{"verdict":"pass"}']), config())
    ctx, _, _ = context()
    with patch("agent_platform.staged_adapter.retrieve_skill_material", return_value=([], "")), \
         patch("agent_platform.staged_adapter.select_strategy_skills", return_value=[]), \
         patch("agent_platform.staged_adapter.theorem_cards", return_value=""):
        assert asyncio.run(runtime.run(ctx)).final_response == r"\boxed{2}"
    assert len(runtime.client.calls) == 5


def test_retrieve_uses_the_same_stage_adapter_with_failure_degradation():
    runtime = LangGraphRuntime(ScriptedClient([
        '{}', '{"risk_level":"low"}', draft(), '{"verdict":"pass"}', '{"verdict":"pass"}',
    ]), replace(config(), staged_strategy_retrieval_enabled=True))
    ctx, events, _ = context()
    with patch("agent_platform.staged_adapter.retrieve_skill_material", return_value=([], "")), \
         patch("agent_platform.staged_adapter.select_strategy_skills", return_value=[]), \
         patch("agent_platform.staged_adapter.theorem_cards", return_value=""), \
         patch("agent_platform.tools.local.LocalTools.strategy_search", side_effect=RuntimeError("private retrieval failure")):
        assert asyncio.run(runtime.run(ctx)).final_response
    assert any(stage == "retrieve" and kind == "retrieval.completed" for stage, kind, _ in events)


def test_retrieval_success_preserves_reference_metadata_not_raw_sources():
    from unittest.mock import Mock
    retriever = Mock()
    retriever.retrieve_for_structure.return_value = {
        "retrieval_text": "structured terms", "index_version": "fixture-v1",
        "results": [{"id": 7, "name": "Transformation", "score": .5,
                     "description": "Preserve the original conditions.", "tags": ["algebra"],
                     "steps": [], "raw_response": "PRIVATE_SOURCE_BLOB"}],
    }
    structure = "Domain: algebra\nGoal: compute\nObjects: variables\nStructure:\n- transformation"
    runtime = LangGraphRuntime(ScriptedClient(['{}', '{"risk_level":"low"}', draft(),
                                              '{"verdict":"pass"}', '{"verdict":"pass"}']),
                               replace(config(), staged_strategy_retrieval_enabled=True))
    ctx, events, _ = context()
    with patch("reasoning_agent.lexical_strategy_retrieval.get_shared_lexical_strategy_retriever", return_value=retriever):
        assert asyncio.run(runtime.run(ctx)).final_response
    completed = [data for _, kind, data in events if kind == "retrieval.completed"]
    assert completed[0]["references"][0]["id"] == "7"
    assert "PRIVATE_SOURCE_BLOB" not in json.dumps(events)


def test_old_and_graph_runtime_protocol_comparison():
    from reasoning_agent.custom2.agent import Custom2Agent

    old_client, new_client = client_for_pass(), client_for_pass()
    ctx, events, _ = context()
    old = Custom2Agent(old_client, config()).solve(ctx.problem, None)
    new = asyncio.run(LangGraphRuntime(new_client, config()).run(ctx))
    assert old["final_response"] == new.final_response == r"\boxed{2}"
    assert len(old_client.calls) == len(new_client.calls) == 5
    assert sum(kind == "model.completed" for _, kind, _ in events) == 5


def test_api_real_graph_with_persistent_store_and_health():
    pytest.importorskip("fastapi")
    fakeredis = pytest.importorskip("fakeredis")
    from fastapi.testclient import TestClient
    from agent_platform.app import create_app
    from agent_platform.redis_store import RedisTaskStore

    store = RedisTaskStore(fakeredis.FakeRedis(decode_responses=True), require_aof=False)
    with TestClient(create_app(store=store, runtime=LangGraphRuntime(client_for_pass(), config()),
                              rate_limits=False)) as client:
        assert client.get("/health/ready").json()["storage"] == "redis_reference"
        session = client.post("/v1/sessions", json={}).json()["id"]
        response = client.post(f"/v1/sessions/{session}/tasks", json={"problem": "Compute a value."}).json()
        stream = client.get(response["events_url"])
        assert "model.completed" in stream.text
        assert "task.succeeded" in stream.text
        assert client.get(response["status_url"]).json()["final_response"] == r"\boxed{2}"
        from agent_platform.models import PlatformError
        with patch.object(store, "ready", side_effect=PlatformError("storage_unavailable", 503)):
            assert client.get("/health/ready").status_code == 503


def test_incompatible_checkpoint_discovery_is_visible_and_not_retried():
    fakeredis = pytest.importorskip("fakeredis")
    from agent_platform.redis_store import RedisTaskStore

    async def check():
        store = RedisTaskStore(fakeredis.FakeRedis(decode_responses=True), require_aof=False)
        session = store.create_session(0)
        task, _ = store.create_task(session.id, "input", {}, "langgraph_staged", None)
        started = store.start(session.id, task.id, 1200)
        store.progress(session.id, task.id, started.generation, "profile", True, {"schema_version": "bad"})
        store.finish(session.id, task.id, started.generation, TaskStatus.INTERRUPTED)
        service = TaskService(store, LangGraphRuntime(ScriptedClient([]), config()), recovery_poll_seconds=.01)
        await service.start()
        await asyncio.sleep(.05)
        await service.stop()
        assert store.get_task(session.id, task.id).error_code == "checkpoint_incompatible"
        events = store.events_after(session.id, task.id, 0)
        assert len([event for event in events if event.event_type == "checkpoint.incompatible"]) == 1
    asyncio.run(check())
