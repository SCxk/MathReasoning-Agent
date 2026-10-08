from typing import Any

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom.parsers.final_answer_parser import normalize_final_response
from reasoning_agent.custom.pipeline.orchestrator import PipelineOrchestrator
from reasoning_agent.custom.state import TaskResult
from reasoning_agent.custom.tools.executor import ToolExecutor


class TaskRunner:
    """Runs one problem from input normalization to final response."""

    def __init__(
        self,
        client: Any,
        tools: dict[str, Any],
        config: AgentConfig,
    ) -> None:
        self.client = client
        self.config = config
        self.tool_executor = ToolExecutor(tools=tools, config=config)
        self.pipeline = PipelineOrchestrator(
            client=client,
            tool_executor=self.tool_executor,
            agent_config=config,
        )

    def run(self, problem: str, metadata: dict | None) -> TaskResult:
        result = self.pipeline.run(problem=problem, metadata=metadata)
        return TaskResult(
            final_response=normalize_final_response(
                result.final_response,
                problem=problem,
            ),
            trace=result.trace,
            debug_trace=result.debug_trace,
        )
