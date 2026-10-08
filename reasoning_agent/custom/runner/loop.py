from typing import Any

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom.runner.context import RunnerContext
from reasoning_agent.custom.errors import (
    EmptyModelResponse,
    ModelBudgetExceeded,
    ToolBudgetExceeded,
)
from reasoning_agent.custom.runner.events import (
    FinalAnswerEvent,
    InvalidEvent,
    SolveStepEvent,
    ToolCallEvent,
)
from reasoning_agent.custom.parsers.final_answer_parser import fallback_answer
from reasoning_agent.custom.parsers.tool_call_parser import parse_model_event
from reasoning_agent.custom.runner.policy import RunnerPolicy
from reasoning_agent.custom.prompts.tool_use import (
    build_force_final_answer_message,
    build_invalid_json_message,
    build_observation_message,
    build_solve_state_message,
    build_tool_result_message,
)
from reasoning_agent.custom.prompts.step_verifier import build_logic_retry_message
from reasoning_agent.custom.state import Candidate
from reasoning_agent.custom.tools.executor import ToolExecutor
from reasoning_agent.custom.verifier.step_verifier import StepLogicVerifier
from reasoning_agent.max_token_retry import (
    call_with_max_token_retry,
    build_retry_max_token_schedule,
)


class ToolUseRunner:
    """Controlled ReAct-style loop for one problem."""

    def __init__(
        self,
        client: Any,
        tool_executor: ToolExecutor,
        config: AgentConfig,
        step_verifier: StepLogicVerifier | None = None,
    ) -> None:
        self.client = client
        self.tool_executor = tool_executor
        self.config = config
        self.policy = RunnerPolicy(config)
        self.step_verifier = step_verifier or StepLogicVerifier(client=client, config=config)

    def run(self, ctx: RunnerContext) -> Candidate:
        while not self.policy.should_stop(ctx):
            raw = self._chat(ctx)
            event = parse_model_event(raw)

            if isinstance(event, FinalAnswerEvent):
                ctx.solve_state.set_final_answer(
                    answer=event.answer,
                    reasoning_summary=event.reasoning_summary,
                )
                return Candidate(
                    answer=event.answer,
                    source="tool_loop",
                    reasoning_summary=event.reasoning_summary,
                )

            if isinstance(event, SolveStepEvent):
                if len(ctx.solve_state.solve_steps) >= self.config.max_solve_steps:
                    state_summary = ctx.solve_state.summary(self.config.max_solve_steps)
                    ctx.debug_trace.append(
                        {
                            "type": "force_final_answer",
                            "content": state_summary,
                        }
                    )
                    ctx.messages.append(build_force_final_answer_message(state_summary))
                    ctx.loop_steps += 1
                    continue

                step = {
                    "step_summary": event.step_summary,
                    "known_facts": event.known_facts,
                    "derived_results": event.derived_results,
                    "remaining_tasks": event.remaining_tasks,
                    "is_ready_for_final": event.is_ready_for_final,
                }
                verify_result = self.step_verifier.verify(ctx, step)
                if verify_result.verdict == "reject":
                    ctx.solve_state.add_error_memory(
                        reason=verify_result.reason,
                        retry_instruction=verify_result.retry_instruction,
                        rejected_step=step,
                        max_items=self.config.max_error_memory_items,
                    )
                    ctx.debug_trace.append(
                        {
                            "type": "step_rejected",
                            "content": {
                                "reason": verify_result.reason,
                                "retry_instruction": verify_result.retry_instruction,
                                "current_logic_retries": ctx.current_logic_retries,
                            },
                        }
                    )
                    if ctx.current_logic_retries < self.config.max_logic_retries:
                        ctx.current_logic_retries += 1
                        retry_message = build_logic_retry_message(
                            reason=verify_result.reason,
                            retry_instruction=verify_result.retry_instruction,
                            state_summary=ctx.solve_state.summary(
                                self.config.max_solve_steps
                            ),
                        )
                        ctx.messages.append(retry_message)
                        ctx.debug_trace.append(
                            {
                                "type": "user",
                                "content": str(retry_message.get("content", "")),
                            }
                        )
                        ctx.loop_steps += 1
                        continue
                    ctx.debug_trace.append(
                        {
                            "type": "force_final_answer",
                            "content": {
                                "reason": "local logic retry budget exhausted; do not accept rejected step",
                                "state": ctx.solve_state.summary(
                                    self.config.max_solve_steps
                                ),
                            },
                        }
                    )
                    ctx.messages.append(
                        build_force_final_answer_message(
                            ctx.solve_state.summary(self.config.max_solve_steps)
                        )
                    )
                    ctx.loop_steps += 1
                    continue
                elif verify_result.verdict == "revise":
                    step = verify_result.revised_step
                    ctx.current_logic_retries = 0
                    ctx.debug_trace.append(
                        {
                            "type": "step_revised",
                            "content": {
                                "reason": verify_result.reason,
                                "step": step,
                            },
                        }
                    )
                else:
                    ctx.current_logic_retries = 0
                ctx.solve_state.add_solve_step(step)
                ctx.debug_trace.append({"type": "solve_step", "content": step})
                state_summary = ctx.solve_state.summary(self.config.max_solve_steps)
                ctx.debug_trace.append(
                    {"type": "state", "content": state_summary}
                )
                ctx.messages.append(build_solve_state_message(state_summary))
                ctx.loop_steps += 1
                continue

            if isinstance(event, ToolCallEvent):
                if not self.policy.can_call_tool(ctx):
                    raise ToolBudgetExceeded("tool call budget exhausted")
                ctx.tool_calls += 1
                ctx.debug_trace.append(
                    {
                        "type": "tool_call",
                        "tool": event.name,
                        "arguments": event.arguments,
                    }
                )
                observation = self.tool_executor.execute(event.name, event.arguments)
                ctx.add_observation(observation)
                ctx.solve_state.add_tool_result(event.name, observation)
                ctx.debug_trace.append(
                    {
                        "type": "tool_call_result",
                        "tool": event.name,
                        "content": observation,
                    }
                )
                if event.assistant_message is not None and event.call_id:
                    ctx.messages.append(event.assistant_message)
                    ctx.messages.append(
                        build_tool_result_message(
                            observation=observation,
                            tool_call_id=event.call_id,
                        )
                    )
                else:
                    ctx.messages.append(build_observation_message(observation))
                ctx.loop_steps += 1
                continue

            if isinstance(event, InvalidEvent):
                ctx.errors.append({"type": "InvalidModelResponse", "message": event.message})
                ctx.solve_state.add_invalid_json()
                ctx.debug_trace.append(
                    {
                        "type": "invalid_json",
                        "content": {"message": event.message},
                    }
                )
                retry_message = build_invalid_json_message(event.message)
                ctx.messages.append(retry_message)
                ctx.debug_trace.append(
                    {
                        "type": "user",
                        "content": str(retry_message.get("content", "")),
                    }
                )
                ctx.loop_steps += 1
                continue

        raise ModelBudgetExceeded("model call budget exhausted")

    def _chat(self, ctx: RunnerContext) -> str | dict[str, Any]:
        if ctx.model_calls >= self.config.max_model_calls:
            raise ModelBudgetExceeded("model call budget exhausted")

        ctx.model_calls += 1
        ctx.loop_steps += 1
        chat_tools = self.tool_executor.chat_tools()
        response = call_with_max_token_retry(
            self.client.chat,
            messages=ctx.messages,
            temperature=self.config.tool_loop_temperature,
            thinking_mode=self.config.thinking_mode,
            tools=chat_tools or None,
            max_token_schedule=build_retry_max_token_schedule(
                getattr(self.client, "retry", 3),
                initial_max_tokens=self.config.tool_loop_max_tokens,
            ),
            result_validator=self._ensure_non_empty_response,
        )

        content = self._response_content(response)
        stored_text = content[: self.config.max_trace_chars]
        ctx.raw_responses.append(stored_text)
        ctx.debug_trace.append(
            {
                "type": "model_call",
                "content": stored_text,
            }
        )
        return response.strip() if isinstance(response, str) else response

    @staticmethod
    def _ensure_non_empty_response(response: str | dict[str, Any]) -> None:
        if isinstance(response, str) and response.strip():
            return
        if isinstance(response, dict):
            content = response.get("content")
            tool_calls = response.get("tool_calls")
            if isinstance(content, str) and content.strip():
                return
            if isinstance(tool_calls, list) and tool_calls:
                return
        else:
            raise EmptyModelResponse("client.chat returned empty content")

        raise EmptyModelResponse("client.chat returned empty content")

    @staticmethod
    def _response_content(response: str | dict[str, Any]) -> str:
        if isinstance(response, str):
            return response.strip()
        content = response.get("content")
        return content.strip() if isinstance(content, str) else ""
