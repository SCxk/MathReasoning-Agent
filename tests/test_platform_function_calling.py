import copy
import json
import threading
from unittest.mock import Mock, AsyncMock

import pytest

from agent_platform.staged_adapter import TracedClient
from agent_platform.tools.registry import ToolRegistry
from agent_platform.tools.function_calling import native_supported
from test_platform_tools import context, successful


class NativeClient:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def chat(self, messages, tools=None, **kwargs):
        self.calls.append(copy.deepcopy({"messages": messages, "tools": tools, **kwargs}))
        return self.responses.pop(0)


class MinimalClient:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def chat(self, messages):
        self.calls.append(copy.deepcopy(messages))
        return self.responses.pop(0)


def tool_call(name="math_verify", args=None):
    args = args or {"problem": "Problem", "candidate": "Proof", "checks": ["proof_obligations"]}
    return {"id": "native-id", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def proxy(client, mode="auto"):
    ctx, events = context()
    ctx.function_calling = mode
    local = Mock(invoke=AsyncMock(return_value=successful()))
    ctx.tools = ToolRegistry(local)
    traced = TracedClient(client, ctx, "solve", threading.BoundedSemaphore(1))
    traced.call_type = "solver"
    return traced, ctx, local, events


def test_native_tool_loop_uses_injected_client_and_sanitized_tool_messages():
    client = NativeClient([{"content": None, "tool_calls": [tool_call()], "raw_response": "private"},
                           {"content": "Complete solution"}])
    traced, ctx, local, events = proxy(client)
    result = traced.chat(messages=[{"role": "user", "content": "Problem"}])
    assert result["content"] == "Complete solution" and local.invoke.call_count == 1
    messages = client.calls[-1]["messages"]
    assert messages[-1]["role"] == "tool" and messages[-1]["tool_call_id"] == "native-id"
    assert "private" not in json.dumps(messages)
    assert len(client.calls[0]["tools"]) == 4
    assert len(ctx.tool_calls) == 1 and ctx.solver_calls_used == 2
    assert sum(kind == "model.started" for kind, data in events) == 2


def test_auto_minimal_client_keeps_original_text_contract():
    client = MinimalClient(["Original result"])
    traced, ctx, local, _ = proxy(client)
    assert traced.chat(messages=[]) == "Original result"
    assert not native_supported(client) and local.invoke.call_count == 0


def test_explicit_json_protocol_for_minimal_injected_client():
    call = tool_call()["function"]
    call["arguments"] = json.loads(call["arguments"])
    client = MinimalClient([json.dumps({"tool_calls": [call]}), "Complete solution"])
    traced, ctx, local, _ = proxy(client, "json")
    assert traced.chat(messages=[]) == "Complete solution"
    assert local.invoke.call_count == 1 and len(ctx.tool_calls) == 1
    assert client.calls[0][0]["role"] == "system"
    assert client.calls[-1][-1]["role"] == "user"


@pytest.mark.parametrize("call", [
    {}, {"id": "x", "function": {"name": "math_verify", "arguments": "{invalid"}},
    {"id": "x", "function": {"name": "math_verify", "arguments": "x" * 65537}},
    {"id": None, "function": {"name": "unknown", "arguments": "{}"}},
    {"function": {"name": 3, "arguments": []}},
])
def test_malformed_function_requests_produce_structured_errors_not_execution(call):
    client = NativeClient([{"tool_calls": [call]}, {"content": "Candidate preserved"}])
    traced, ctx, local, events = proxy(client)
    assert traced.chat(messages=[])["content"] == "Candidate preserved"
    assert local.invoke.call_count == 0
    assert json.loads(client.calls[-1]["messages"][-1]["content"])["status"] == "failed"


@pytest.mark.parametrize("calls", [[tool_call()] * 5, "not-a-list"])
def test_excessive_function_requests_are_bounded(calls):
    traced, ctx, local, _ = proxy(NativeClient([{"tool_calls": calls}]))
    with pytest.raises(ValueError, match="function_call_budget"):
        traced.chat(messages=[])
    assert not ctx.tool_calls


def test_tool_turn_budget_and_solver_budget_are_not_reset():
    traced, ctx, local, _ = proxy(NativeClient([{"tool_calls": [tool_call()]}] * 3))
    with pytest.raises(ValueError):
        traced.chat(messages=[])
    assert ctx.solver_calls_used == 3 and local.invoke.call_count == 2


@pytest.mark.parametrize("mode", ["off", "json"])
def test_disabled_or_plain_json_response_has_no_tool_call(mode):
    client = NativeClient(["not json"])
    traced, _, local, _ = proxy(client, mode)
    assert traced.chat(messages=[]) == "not json" and local.invoke.call_count == 0


def test_nonsolver_calls_do_not_get_tool_definitions():
    client = NativeClient(["profile"])
    traced, _, _, _ = proxy(client, "native")
    traced.call_type = "classifier"
    assert traced.chat(messages=[]) == "profile"
    assert client.calls[0]["tools"] is None


def test_capability_introspection_and_original_call_deadline():
    from unittest.mock import patch
    client = MinimalClient([])
    client.supports_tools = True
    assert native_supported(client)
    client.supports_tools = False
    with patch("agent_platform.tools.function_calling.inspect.signature", side_effect=ValueError):
        assert not native_supported(client)
    traced, _, _, _ = proxy(NativeClient([]))
    with pytest.raises(TimeoutError):
        traced.chat(messages=[], request_timeout=-1)


def test_bad_native_call_identifier_is_rejected_before_execution():
    call = tool_call()
    call["id"] = None
    traced, _, local, _ = proxy(NativeClient([{"tool_calls": [call]}, "candidate"]))
    assert traced.chat(messages=[]) == "candidate"
    assert local.invoke.call_count == 0
