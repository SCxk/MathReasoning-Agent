"""Private stdio server using the official MCP Python SDK."""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, Tool, ToolAnnotations
from pydantic import create_model, ValidationError

from agent_platform.tools.local import LocalTools
from agent_platform.tools.registry import failure, validated_result
from agent_platform.tools.schemas import ARGUMENTS, VALUES, SCHEMA_VERSION, ToolResult, definitions


EXPOSED = ("strategy_search", "math_verify")


def output_schema(name):
    return create_model(f"{name}_result", __base__=ToolResult,
                        value=(VALUES[name] | None, None)).model_json_schema()


def tool_definitions():
    specs = {item["function"]["name"]: item["function"] for item in definitions()}
    return [Tool(name=name, description=specs[name]["description"],
                 inputSchema=ARGUMENTS[name].model_json_schema(), outputSchema=output_schema(name),
                 meta={"schema_version": SCHEMA_VERSION},
                 annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False))
            for name in EXPOSED]


def create_server(local=None):
    local = local or LocalTools()
    server = Server("maths-single-agent-tools", version=SCHEMA_VERSION)

    @server.list_tools()
    async def list_tools():
        return tool_definitions()

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        if name not in EXPOSED:
            result = failure("unknown_tool")
        else:
            try:
                args = ARGUMENTS[name].model_validate(arguments).model_dump()
            except ValidationError:
                result = failure("invalid_arguments")
            else:
                try:
                    result = validated_result(name, await asyncio.wait_for(local.invoke(name, args), 30))
                except TimeoutError:
                    result = failure("timeout", retryable=True)
                except (ValueError, TypeError):
                    result = failure("invalid_result")
                except Exception:
                    result = failure("execution_error")
        # Do not echo SDK validation diagnostics containing request data.
        return CallToolResult(content=[], structuredContent=result.model_dump(),
                              isError=result.status == "failed")

    return server


async def main():
    server = create_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":  # pragma: no cover - exercised by actual SDK stdio integration.
    asyncio.run(main())
