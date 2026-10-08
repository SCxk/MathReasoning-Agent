"""Abrupt SDK tool-server exit used only by deterministic transport tests."""

import asyncio
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.stdio import stdio_server
from agent_platform.tools.mcp_server import create_server


class CrashTool:
    async def invoke(self, name, arguments):
        os._exit(31)


async def main():
    server = create_server(CrashTool())
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
