from typing import Any

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom.parsers.final_answer_parser import normalize_final_response
from reasoning_agent.custom.parsers.json_parser import make_json_safe
from reasoning_agent.custom.task_runner import TaskRunner
from reasoning_agent.custom.tools.registry import build_tool_registry


class CustomAgent:
    """Default reasoning implementation backed by TaskRunner."""

    def __init__(
        self,
        client: Any,
        config: AgentConfig | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.client = client
        self.config = config or AgentConfig()
        self.tools = build_tool_registry()

    def solve(self, problem: str, metadata: dict | None) -> dict:
        runner = TaskRunner(
            client=self.client,
            tools=self.tools,
            config=self.config,
        )
        result = runner.run(problem=problem, metadata=metadata)
        output = {
            "final_response": normalize_final_response(
                result.final_response,
                problem=problem,
            ),
            "trace": make_json_safe(result.trace),
        }
        if self.config.emit_debug_trace:
            output["debug_trace"] = make_json_safe(result.debug_trace)
        return output
