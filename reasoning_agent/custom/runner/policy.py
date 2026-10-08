from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom.runner.context import RunnerContext


class RunnerPolicy:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def should_stop(self, ctx: RunnerContext) -> bool:
        return (
            ctx.loop_steps >= self.config.max_loop_steps
            or ctx.model_calls >= self.config.max_model_calls
        )

    def can_call_tool(self, ctx: RunnerContext) -> bool:
        return ctx.tool_calls < self.config.max_tool_calls
