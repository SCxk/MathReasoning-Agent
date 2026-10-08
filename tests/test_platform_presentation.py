"""Chat presentation fixtures test protocol behavior, not model answer quality."""

import asyncio
import copy
import json
import time
from unittest.mock import patch

import fakeredis
import pytest
from fastapi.testclient import TestClient

from agent_platform.app import create_app
from agent_platform.graph_runtime import LangGraphRuntime
from agent_platform.models import Message
from agent_platform.presentation import (
    RESPONSE_STYLE_KEY,
    public_sections,
    render_chat_response,
    requested_style,
)
from agent_platform.redis_store import RedisTaskStore
from agent_platform.runtime import CheckpointIncompatible, FakeRuntime
from agent_platform.staged_adapter import StagedAdapter
from reasoning_agent.custom2.staged_models import StagedAudit, StagedModelFidelity
from test_platform_graph import ScriptedClient, client_for_pass, config, context, draft
from agent_platform.questions_parser import INSTRUCTION_KEY


@pytest.mark.parametrize("style", ["auto", "detailed"])
def test_attachment_instruction_reaches_models_without_rewriting_problem(style):
    client = ScriptedClient([
        '{"answer_mode":"computation","response_style":"answer"}',
        '{"risk_level":"high"}', draft(), '{"verdict":"pass"}', '{"verdict":"pass"}',
    ])
    ctx, _, _ = context()
    original = ctx.problem
    ctx.metadata = {RESPONSE_STYLE_KEY: style, INSTRUCTION_KEY: "Please explain using algebra."}
    result = asyncio.run(LangGraphRuntime(client, config()).run(ctx))
    assert ctx.problem == original
    for index in [0, 2, 3, 4]:
        assert "Please explain using algebra." in json.dumps(client.calls[index])
        assert "user_answer_request" in json.dumps(client.calls[index])
    assert ("## 问题分析" in result.final_response) == (style == "detailed")
    assert len(client.calls) == 5


@pytest.mark.parametrize("style", ["answer", "brief", "detailed"])
def test_only_requested_public_sections_are_rendered(style):
    result = render_chat_response(draft(), "computation", style)
    assert r"\boxed{2}" in result
    assert ("## 详细解题步骤" in result) == (style != "answer")
    assert ("## 问题分析" in result) == (style == "detailed")
    assert ("## 关键验证点" in result) == (style == "detailed")
    if style != "answer":
        assert "The defining calculation gives the result." in result


@pytest.mark.parametrize("mode", ["computation", "choice", "fill_blank", "other"])
def test_chat_answer_preserves_multipart_markdown_without_competition_boxing(mode):
    final = "1. $u=4$.\n2. The interval is $(a,b)$.\n3. The bound is $q$ and uses the given condition."
    result = render_chat_response(draft().replace(r"\boxed{2}", final), mode, "answer")
    assert result == final
    assert r"\boxed{" not in result
    assert "详细解题步骤" not in result


@pytest.mark.parametrize("style", ["answer", "brief", "detailed"])
def test_proof_body_is_never_replaced_by_a_bare_conclusion(style):
    result = render_chat_response(draft("Conclusion follows.", proof=True), "proof", style)
    assert "The defining calculation gives the result." in result
    assert "Conclusion follows." in result


@pytest.mark.parametrize("fence", ["```", "~~~~"])
def test_internal_checks_and_private_thoughts_are_not_public(fence):
    candidate = draft().replace(
        "## 详细解题步骤\n",
        "## 详细解题步骤\n"
        f"<think>PRIVATE_THOUGHT</think>\n{fence}check\nINTERNAL_CHECK\n"
        f"## 最终答案\n{fence}\n",
    )
    candidate += "\n## Internal log\nPRIVATE_LOG"
    candidate = "PRIVATE_PREAMBLE\n" + candidate
    for style in ("brief", "detailed"):
        result = render_chat_response(candidate, "computation", style)
        assert "PRIVATE_" not in result and "INTERNAL_CHECK" not in result
        assert "The defining calculation gives the result." in result
        assert r"\boxed{2}" in result


def test_markdown_headings_inside_code_do_not_change_solution_sections():
    candidate = draft().replace(
        "## 详细解题步骤\n",
        "## 详细解题步骤\n```text\n## 最终答案\nLiteral example, not a result.\n```\n",
    )
    sections = public_sections(candidate)
    assert "Literal example" in sections["详细解题步骤"]
    assert sections["最终答案"] == r"\boxed{2}"
    assert render_chat_response(candidate, "computation", "answer") == r"\boxed{2}"


@pytest.mark.parametrize("private", ["<think>", "<analysis>", "```check\n", "~~~check\n"])
def test_unfinished_private_blocks_fail_closed(private):
    candidate = "## 详细解题步骤\nVisible step.\n" + private + "PRIVATE_TAIL"
    result = render_chat_response(candidate, "computation", "brief")
    assert "Visible step." in result and "PRIVATE_TAIL" not in result
    assert "无法确定唯一答案" in result


def test_partial_candidates_do_not_invent_missing_steps_or_leak_thought_answers():
    result = render_chat_response(r"\boxed{2}", "computation", "brief")
    assert "未生成可展示的解题过程" in result and r"\boxed{2}" in result
    private = r"<think>\boxed{PRIVATE_THOUGHT}</think>"
    assert render_chat_response(private, "computation", "answer") == "无法确定唯一答案"
    assert "无法确定唯一答案" in render_chat_response("", "computation", "detailed")
    with pytest.raises(ValueError, match="unresolved_response_style"):
        render_chat_response(draft(), "computation", "auto")


def test_public_solution_uses_existing_secret_and_path_sanitization():
    candidate = draft().replace(
        "The defining calculation",
        "password=fixture-value C:\\private\\file The defining calculation",
    )
    result = render_chat_response(candidate, "computation", "detailed")
    assert "fixture-value" not in result and "C:" not in result
    assert "[redacted]" in result and "[local path]" in result


@pytest.mark.parametrize("invalid", ["unknown", {}, [], 1])
def test_metadata_style_must_be_declared_enum(invalid):
    with pytest.raises(ValueError, match="invalid_response_style"):
        requested_style({RESPONSE_STYLE_KEY: invalid})


@pytest.mark.parametrize("style", ["answer", "brief", "detailed"])
def test_chat_adapter_preserves_client_and_only_changes_presentation(style):
    runtime = LangGraphRuntime(client_for_pass(), config())
    ctx, events, states = context()
    ctx.metadata = {RESPONSE_STYLE_KEY: style}
    result = asyncio.run(runtime.run(ctx))
    assert len(runtime.client.calls) == 5
    assert result.final_response == render_chat_response(draft(), "computation", style)
    assert ctx.saved_response == result.final_response
    assert all(state["response_style"] == style for state in states)
    assert all(state["adapter"]["_response_style"] == style for state in states)
    assert "聊天展示要求" in runtime.client.calls[2]["messages"][0]["content"]
    assert all("## 详细解题步骤" not in json.dumps(payload) for _, _, payload in events)


@pytest.mark.parametrize(
    "inferred,expected",
    [
        ("answer", "brief"),
        ("brief", "brief"),
        ("detailed", "detailed"),
        ("unknown", "brief"),
        (None, "brief"),
        ({}, "brief"),
    ],
)
def test_auto_style_is_classified_in_the_existing_call_and_validated(inferred, expected):
    classifier = json.dumps(
        {"domain": "linear_algebra", "answer_mode": "computation", "response_style": inferred}
    )
    client = ScriptedClient(
        [classifier, '{"risk_level":"high"}', draft(), '{"verdict":"pass"}', '{"verdict":"pass"}']
    )
    ctx, _, states = context()
    ctx.metadata = {RESPONSE_STYLE_KEY: "auto"}
    ctx.problem += " Give a brief explanation."
    ctx.memory = (Message("old", "user", "Untrusted previous presentation preference.", "other"),)
    result = asyncio.run(LangGraphRuntime(client, config()).run(ctx))
    assert len(client.calls) == 5
    assert "response_style" in client.calls[0]["messages"][0]["content"]
    assert "Untrusted previous presentation preference" not in json.dumps(client.calls[0])
    assert states[0]["profile"]["domain"] == "linear_algebra"
    assert states[0]["adapter"]["_response_style"] == expected
    assert result.final_response == render_chat_response(draft(), "computation", expected)


@pytest.mark.parametrize("evidence,expected", [("Only show the final result.", "answer"), ("", "brief"), ("   ", "brief"), (None, "brief"), ("invented quote", "brief"), ({}, "brief")])
def test_auto_answer_needs_an_exact_current_request_quote(evidence, expected):
    client = ScriptedClient([
        json.dumps({"answer_mode": "computation", "response_style": "answer", "response_style_evidence": evidence}),
        '{"risk_level":"high"}', draft(), '{"verdict":"pass"}', '{"verdict":"pass"}',
    ])
    ctx, _, states = context()
    ctx.problem += " Only show the final result."
    ctx.metadata = {RESPONSE_STYLE_KEY: "auto"}
    result = asyncio.run(LangGraphRuntime(client, config()).run(ctx))
    assert result.final_response == render_chat_response(draft(), "computation", expected)
    assert states[0]["adapter"]["_response_style"] == expected
    assert "response_style_evidence" not in states[0]["profile"]
    assert len(client.calls) == 5


def test_attachment_answer_only_quote_takes_precedence_and_is_not_checkpointed():
    instruction = "Only show the final result."
    client = ScriptedClient([
        json.dumps({"answer_mode": "computation", "response_style": "answer", "response_style_evidence": instruction}),
        '{"risk_level":"high"}', draft(), '{"verdict":"pass"}', '{"verdict":"pass"}',
    ])
    ctx, _, states = context()
    ctx.problem += " Explain the reasoning."
    ctx.metadata = {RESPONSE_STYLE_KEY: "auto", INSTRUCTION_KEY: instruction}
    result = asyncio.run(LangGraphRuntime(client, config()).run(ctx))
    assert result.final_response == render_chat_response(draft(), "computation", "answer")
    assert states[0]["adapter"]["_response_style"] == "answer"
    assert "response_style_evidence" not in json.dumps(states)
    assert len(client.calls) == 5


def test_attachment_preferences_cannot_be_overridden_by_a_problem_answer_only_quote():
    client = ScriptedClient([
        '{"answer_mode":"computation","response_style":"answer","response_style_evidence":"Only show the final result."}',
        '{"risk_level":"high"}', draft(), '{"verdict":"pass"}', '{"verdict":"pass"}',
    ])
    ctx, _, _ = context()
    ctx.problem += " Only show the final result."
    ctx.metadata = {RESPONSE_STYLE_KEY: "auto", INSTRUCTION_KEY: "Explain the reasoning."}
    assert "## 详细解题步骤" in asyncio.run(LangGraphRuntime(client, config()).run(ctx)).final_response


def test_explicit_ui_choice_is_not_overridden_by_a_classifier_extra_field():
    client = ScriptedClient(
        [
            '{"domain":"linear_algebra","response_style":"answer"}',
            '{"risk_level":"high"}',
            draft(),
            '{"verdict":"pass"}',
            '{"verdict":"pass"}',
        ]
    )
    ctx, _, _ = context()
    ctx.metadata = {RESPONSE_STYLE_KEY: "detailed"}
    result = asyncio.run(LangGraphRuntime(client, config()).run(ctx))
    assert "## 问题分析" in result.final_response


@pytest.mark.parametrize("style", ["brief", "detailed", "auto"])
def test_resume_at_every_checkpoint_keeps_style_and_does_not_replay_calls(style):
    ctx, _, states = context()
    ctx.metadata = {RESPONSE_STYLE_KEY: style}
    result = asyncio.run(LangGraphRuntime(client_for_pass(), config()).run(ctx))
    remaining = [
        ['{"risk_level":"high"}', draft(), '{"verdict":"pass"}', '{"verdict":"pass"}'],
        ['{"risk_level":"high"}', draft(), '{"verdict":"pass"}', '{"verdict":"pass"}'],
        [draft(), '{"verdict":"pass"}', '{"verdict":"pass"}'],
        ['{"verdict":"pass"}', '{"verdict":"pass"}'],
        ['{"verdict":"pass"}', '{"verdict":"pass"}'],
        [],
        [],
    ]
    for checkpoint, responses in zip(states, remaining):
        resumed, _, _ = context(checkpoint, ctx.deadline_at)
        resumed.metadata = ctx.metadata
        client = ScriptedClient(responses)
        assert (
            asyncio.run(LangGraphRuntime(client, config()).run(resumed)).final_response
            == result.final_response
        )
        assert len(client.calls) == len(responses)
        assert resumed.saved_response == result.final_response


def test_checkpoint_binds_requested_and_resolved_style():
    runtime = LangGraphRuntime(client_for_pass(), config())
    ctx, _, states = context()
    ctx.metadata = {RESPONSE_STYLE_KEY: "brief"}
    asyncio.run(runtime.run(ctx))
    resumed, _, _ = context(states[0], ctx.deadline_at)
    resumed.metadata = {RESPONSE_STYLE_KEY: "detailed"}
    with pytest.raises(CheckpointIncompatible):
        asyncio.run(runtime.run(resumed))
    for value in ["detailed", {}, "bad"]:
        checkpoint = copy.deepcopy(states[0])
        checkpoint["adapter"]["_response_style"] = value
        assert not runtime.checkpoint_compatible(checkpoint)


@pytest.mark.parametrize("accepted", [False, True])
def test_repair_and_verify_failure_keep_the_matching_candidate_steps(accepted):
    client = ScriptedClient(
        [
            '{"answer_mode":"computation"}',
            '{"risk_level":"high"}',
            draft().replace("defining calculation", "original calculation"),
            draft("7").replace("defining calculation", "repaired calculation"),
        ]
    )
    ctx, _, _ = context()
    ctx.metadata = {RESPONSE_STYLE_KEY: "brief", INSTRUCTION_KEY: "Keep the algebraic explanation."}
    with (
        patch.object(
            StagedAdapter, "_model_fidelity", return_value=StagedModelFidelity(verdict="pass")
        ),
        patch.object(
            StagedAdapter,
            "_audit",
            side_effect=[
                StagedAudit(verdict="fail", first_fatal_error="fixture defect"),
                StagedAudit(
                    verdict="pass" if accepted else "fail", first_fatal_error="fixture defect"
                ),
            ],
        ),
    ):
        result = asyncio.run(LangGraphRuntime(client, config(custom2_max_repairs=1)).run(ctx))
    assert ("repaired calculation" in result.final_response) == accepted
    assert ("original calculation" in result.final_response) != accepted
    assert (r"\boxed{7}" if accepted else r"\boxed{2}") in result.final_response
    assert ctx.saved_response == result.final_response
    for call in client.calls[2:]:
        assert "Keep the algebraic explanation." in json.dumps(call)


def test_exception_fallback_preserves_solution_steps():
    ctx, _, _ = context()
    ctx.metadata = {RESPONSE_STYLE_KEY: "brief"}
    with patch.object(StagedAdapter, "_model_fidelity", side_effect=RuntimeError("PRIVATE_ERROR")):
        result = asyncio.run(LangGraphRuntime(client_for_pass(), config()).run(ctx))
    assert "The defining calculation" in result.final_response
    assert "PRIVATE_ERROR" not in result.final_response


def test_api_style_validation_defaults_and_idempotency():
    with TestClient(create_app(runtime=FakeRuntime(0.001), rate_limits=False)) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        path = f"/v1/sessions/{session}/tasks"
        assert set(client.get("/health/ready").json()["response_styles"]) == {
            "auto",
            "answer",
            "brief",
            "detailed",
        }
        legacy = client.post(path, json={"problem": "Protocol fixture."}).json()
        assert legacy["response_style"] is None
        for style in ["auto", "answer", "brief", "detailed"]:
            body = {"problem": "Protocol fixture.", "response_style": style}
            headers = {"Idempotency-Key": f"style-{style}"}
            first = client.post(path, json=body, headers=headers)
            assert first.status_code == 202 and first.json()["response_style"] == style
            assert client.post(path, json=body, headers=headers).json()["id"] == first.json()["id"]
            assert (
                client.post(
                    path,
                    json={**body, "response_style": "brief" if style != "brief" else "answer"},
                    headers=headers,
                ).status_code
                == 409
            )
            assert (
                client.app.state.store.get_task(session, first.json()["id"]).metadata[
                    RESPONSE_STYLE_KEY
                ]
                == style
            )
        for invalid in ["raw", {}, 1, []]:
            response = client.post(
                path, json={"problem": "Protocol fixture.", "response_style": invalid}
            )
            assert (
                response.status_code == 400
                and response.json()["error"]["code"] == "invalid_request"
            )
        assert (
            client.post(
                path,
                json={"problem": "Protocol fixture.", "metadata": {RESPONSE_STYLE_KEY: "detailed"}},
            ).status_code
            == 400
        )


@pytest.mark.parametrize("cutoff", [False, True])
def test_api_redis_persistence_sse_and_service_timeout_keep_public_steps(cutoff):
    class CutoffRuntime(LangGraphRuntime):
        async def run(self, ctx):
            result = await super().run(ctx)
            if cutoff:
                raise TimeoutError
            return result

    redis = fakeredis.FakeRedis(decode_responses=True)
    store = RedisTaskStore(redis, require_aof=False)
    with TestClient(
        create_app(
            store=store, runtime=CutoffRuntime(client_for_pass(), config()), rate_limits=False
        )
    ) as client:
        session = client.post("/v1/sessions", json={}).json()["id"]
        task = client.post(
            f"/v1/sessions/{session}/tasks",
            json={"problem": "Protocol fixture.", "response_style": "brief"},
        ).json()
        until = time.monotonic() + 3
        while time.monotonic() < until:
            final = client.get(task["status_url"]).json()
            if final["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.005)
        assert final["status"] == "succeeded"
        assert "The defining calculation" in final["final_response"]
        assert final["response_style"] == "brief"
        events = client.get(task["trace_url"]).json()["events"]
        assert events[-1]["payload"]["final_response"] == final["final_response"]
        frames = [
            json.loads(line[6:])
            for line in client.get(task["events_url"]).text.splitlines()
            if line.startswith("data: ")
        ]
        assert frames[-1]["payload"]["final_response"] == final["final_response"]
        reopened = RedisTaskStore(redis, require_aof=False)
        assert reopened.get_task(session, task["id"]).metadata[RESPONSE_STYLE_KEY] == "brief"
        assert reopened.get_task(session, task["id"]).final_response == final["final_response"]
