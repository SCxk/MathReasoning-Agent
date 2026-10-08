import os
import sys
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agent_platform.tools.mcp_server import EXPOSED, tool_definitions
from agent_platform.tools.registry import validated_result


class SchemaMismatch(ValueError):
    pass


def check_conformance(remote):
    expected = {tool.name: tool for tool in tool_definitions()}
    actual = {tool.name: tool for tool in remote}
    if set(actual) != set(expected):
        raise SchemaMismatch("mcp_schema_mismatch")
    for name, tool in expected.items():
        received = actual[name]
        if (received.inputSchema != tool.inputSchema or received.outputSchema != tool.outputSchema
                or received.meta != tool.meta):
            raise SchemaMismatch("mcp_schema_mismatch")


class SdkMCPClient:
    """Only launches this repository's private, fixed stdio tool server."""

    async def invoke(self, name, arguments):
        try:
            return await self._invoke(name, arguments)
        except ExceptionGroup as group:
            def invalid(children):
                return any(invalid(child.exceptions) if isinstance(child, ExceptionGroup)
                           else isinstance(child, ValueError) for child in children)
            if invalid(group.exceptions):
                raise ValueError("mcp_validation_failed") from None
            raise

    async def _invoke(self, name, arguments):
        if name not in EXPOSED:
            raise ValueError("unsupported_mcp_tool")
        # No model credentials, arbitrary executable, or public network endpoint.
        env = {key: value for key, value in os.environ.items()
               if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG"}}
        params = StdioServerParameters(command=sys.executable,
                                       args=["-m", "agent_platform.tools.mcp_server"], env=env)
        with open(os.devnull, "w") as errors:
            async with stdio_client(params, errlog=errors) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as session:
                    await session.initialize()
                    check_conformance((await session.list_tools()).tools)
                    result = await session.call_tool(name, arguments)
                    parsed = validated_result(name, result.structuredContent)
                    if result.isError != (parsed.status == "failed"):
                        raise ValueError("mcp_result_mismatch")
                    return parsed.model_dump()
