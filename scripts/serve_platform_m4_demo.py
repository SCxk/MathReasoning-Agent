"""Explicit fake workflow showing real local/MCP tool transport, never a math benchmark."""

import argparse
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn
from agent_platform.app import create_app
from agent_platform.runtime import RuntimeResult, STAGES
from agent_platform.tools.mcp_client import SdkMCPClient
from agent_platform.tools.registry import ToolRegistry, stable_call_id
from agent_platform.tools.schemas import ToolInvocation


class ToolProtocolDemo:
    name = "fake_tool_protocol_demo"

    def __init__(self):
        self.tools = ToolRegistry(mcp=SdkMCPClient())

    async def run(self, context):
        completed = (context.checkpoint or {}).get("completed_stage", -1)
        async def invoke(stage, name, args):
            request = ToolInvocation(call_id=stable_call_id(context, stage, "demo", name, args),
                                     task_id=context.task_id, stage_id=stage, tool_name=name, arguments=args)
            await self.tools.invoke(request, context)
        for index, stage in enumerate(STAGES):
            if index <= completed:
                continue
            context.progress(stage)
            await asyncio.sleep(.25)
            if stage == "retrieve":
                await invoke(stage, "strategy_search", {"query": context.problem[:4000], "top_k": 2})
                await invoke(stage, "document_search", {"query": context.problem[:4000], "session_id": context.session_id})
            if stage == "tool":
                await invoke(stage, "sympy_calculate", {"expression": "1+1", "operation": "simplify"})
                await invoke(stage, "math_verify", {"problem": context.problem,
                    "candidate": "Protocol fixture only: $1+1=2$", "checks": ["numeric_equivalence", "proof_obligations"]})
            context.progress(stage, completed=True, checkpoint={"completed_stage": index})
        return RuntimeResult("Fake Runtime completed. Tool protocol fixture only; no mathematical answer was generated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()
    uvicorn.run(create_app(runtime=ToolProtocolDemo()), host="127.0.0.1", port=args.port, access_log=False)
