import asyncio
import copy
from unittest.mock import AsyncMock, Mock

import pytest

pytest.importorskip("mcp")

from agent_platform.tools.mcp_client import SdkMCPClient, SchemaMismatch, check_conformance
from agent_platform.tools.mcp_server import create_server, tool_definitions, EXPOSED
from agent_platform.tools.registry import ToolRegistry
from test_platform_tools import context, request, successful


@pytest.mark.parametrize("change", ["name", "input", "output", "version"])
def test_mcp_schema_drift_is_rejected(change):
    tools = tool_definitions()
    check_conformance(tools)
    if change == "name":
        tools.pop()
    elif change == "input":
        tools[0].inputSchema = {}
    elif change == "output":
        tools[0].outputSchema = {}
    else:
        tools[0].meta = {"schema_version": "other"}
    with pytest.raises(SchemaMismatch):
        check_conformance(tools)


def test_schema_drift_does_not_retry_or_fallback():
    ctx, _ = context()
    remote = Mock(invoke=AsyncMock(side_effect=SchemaMismatch("mismatch")))
    local = Mock(invoke=AsyncMock(return_value=successful()))
    result = asyncio.run(ToolRegistry(local, mcp=remote).invoke(request(ctx), ctx))
    assert result.error_code == "invalid_result"
    assert remote.invoke.call_count == 1 and local.invoke.call_count == 0


def test_actual_sdk_stdio_schema_and_verification_parity():
    from agent_platform.tools.local import LocalTools
    args = {"problem": "Calculate the defined quantity.", "candidate": "$1+1=3$", "checks": ["numeric_equivalence"]}
    async def run():
        remote = await SdkMCPClient().invoke("math_verify", args)
        local = await LocalTools().invoke("math_verify", args)
        assert remote["value"] == local["value"]
        assert remote["value"]["verdict"] == "fail"
        malformed = await SdkMCPClient().invoke("math_verify", {"problem": "p"})
        assert malformed["error_code"] == "invalid_arguments"
        with pytest.raises(ValueError):
            await SdkMCPClient().invoke("sympy_calculate", {})
    asyncio.run(run())


def test_actual_sdk_strategy_search_matches_local_or_reports_same_unavailability():
    from agent_platform.tools.local import LocalTools
    args = {"query": "linear algebra eigenvalue", "top_k": 2}
    async def run():
        local = LocalTools()
        try:
            expected = await local.invoke("strategy_search", args)
        except FileNotFoundError:
            expected = None
        result = await SdkMCPClient().invoke("strategy_search", args)
        if expected is None:
            assert result["error_code"] == "execution_error"
        else:
            assert result["value"] == expected["value"]
    asyncio.run(run())


def test_sdk_exception_group_validation_is_classified():
    client = SdkMCPClient()
    client._invoke = AsyncMock(side_effect=ExceptionGroup("sdk", [SchemaMismatch("mismatch")]))
    with pytest.raises(ValueError, match="mcp_validation_failed"):
        asyncio.run(client.invoke("math_verify", {}))
    client._invoke = AsyncMock(side_effect=ExceptionGroup("sdk", [ConnectionError()]))
    with pytest.raises(ExceptionGroup):
        asyncio.run(client.invoke("math_verify", {}))


@pytest.mark.parametrize("scenario,code", [
    ("success", None), ("unknown", "unknown_tool"), ("invalid_arguments", "invalid_arguments"),
    ("timeout", "timeout"), ("invalid_result", "invalid_result"), ("error", "execution_error"),
])
def test_sdk_server_handler_uses_shared_validation_and_sanitized_errors(scenario, code):
    from mcp.types import CallToolRequest, CallToolRequestParams
    local = Mock(invoke=AsyncMock(return_value=successful()))
    if scenario == "timeout":
        local.invoke.side_effect = TimeoutError
    elif scenario == "invalid_result":
        local.invoke.return_value = {"status": "bad"}
    elif scenario == "error":
        local.invoke.side_effect = RuntimeError("private response")
    server = create_server(local)
    args = {"problem": "p", "candidate": "c", "checks": ["proof_obligations"]}
    req = CallToolRequest(method="tools/call", params=CallToolRequestParams(
        name="unknown" if scenario == "unknown" else "math_verify",
        arguments={} if scenario == "invalid_arguments" else args))
    result = asyncio.run(server.request_handlers[CallToolRequest](req)).root
    assert result.structuredContent["error_code"] == code
    assert result.isError == (code is not None)
    assert "private" not in result.model_dump_json()


def test_sdk_server_stdio_bootstrap_and_list_handler():
    from contextlib import asynccontextmanager
    from unittest.mock import patch
    from agent_platform.tools import mcp_server
    from mcp.types import ListToolsRequest
    server = create_server()
    req = ListToolsRequest(method="tools/list")
    listed = asyncio.run(server.request_handlers[ListToolsRequest](req)).root
    assert {tool.name for tool in listed.tools} == set(EXPOSED)
    server = Mock(run=AsyncMock())
    @asynccontextmanager
    async def streams():
        yield "read", "write"
    with patch.object(mcp_server, "create_server", return_value=server), patch.object(mcp_server, "stdio_server", streams):
        asyncio.run(mcp_server.main())
    server.run.assert_awaited_once()


def test_actual_sdk_server_disconnect_retries_then_uses_equivalent_local_tool():
    from pathlib import Path
    import sys
    from unittest.mock import patch
    from mcp import StdioServerParameters
    fixture = Path(__file__).resolve().parents[1] / "scripts" / "mcp_failure_fixture.py"
    def parameters(**kwargs):
        return StdioServerParameters(command=sys.executable, args=[str(fixture)], env=kwargs["env"])
    ctx, events = context()
    local = Mock(invoke=AsyncMock(return_value=successful()))
    with patch("agent_platform.tools.mcp_client.StdioServerParameters", side_effect=parameters):
        result = asyncio.run(ToolRegistry(local, mcp=SdkMCPClient()).invoke(request(ctx), ctx))
    assert result.status == "fallback" and local.invoke.call_count == 1
    assert len(ctx.tool_calls["call"]["attempts"]) == 3
    assert sum(kind == "tool.failed" for kind, _ in events) == 3
