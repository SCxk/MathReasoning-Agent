import re
from typing import Any

from reasoning_agent.custom.parsers.json_parser import extract_json_object
from reasoning_agent.custom2.context import build_solver_messages
from reasoning_agent.custom2.model_call import call_model
from reasoning_agent.custom2.models import AgentState, Task
from reasoning_agent.custom2.runner import ReasoningRuntime, _normalize_reasoning_step_payload
from reasoning_agent.custom2.schemas import ReasoningStep, ResultProposal
from reasoning_agent.custom2.solution_parser import (
    create_draft, extract_candidate, infer_profile, render_solution,
)


SOLVER_TEXT_SYSTEM_PROMPT = """你是数学推理 Runtime 中的 Solver。本次只改变你的回答格式，任务由原 Runtime 决定。
根据原题、已验证事实、定义、结果和当前任务，给出当前任务的完整自然语言推导。
策略建议不是已证事实；旧草稿、候选和失败记录也不是已验证结论。不要用它们替代证明。
只解决当前任务：如果当前任务就是整题则完整求解，如果是子任务则不要擅自扩展成整题。
不要求 JSON，不要填写 current_task、used_results、new_results、closed_tasks 等状态字段，程序会管理。
说明使用的前提、关键推导、适用条件和本任务结论；证据不足时明确说明缺口，不伪造完成。
子任务结论无需 boxed，也不是整题最终答案。
只有确实得到整题候选答案时，可以在最后写“整题候选答案：”并列出全部结果，不在该段继续推导。
若只是局部结果，不使用这个标题。候选仍需原 Runtime 的审核和验证，不能自行结束流程。
审核指出错误后的 Repair、路线重规划和最终汇总由 Runtime 的其他角色负责。
"""

_CANDIDATE_MARKER = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+)?(?:\*\*)?整题候选答案(?:\*\*)?[ \t]*[:：][ \t]*(?:\*\*)?",
    re.MULTILINE,
)


class SolverTextReasoningRuntime(ReasoningRuntime):
    def __init__(self, client: Any, config: Any | None = None) -> None:
        super().__init__(client, config)
        self.thinking_mode = str(getattr(config, "custom2_text_thinking_mode", "false")).lower()
        if self.thinking_mode not in {"false", "true", "default"}:
            raise ValueError("custom2_text_thinking_mode must be false, true or default")

    def _solve_step(
        self, state: AgentState, debug_trace: list[dict], current_task: Task
    ) -> ReasoningStep | None:
        messages = build_solver_messages(
            state, history_messages=self.solver_history_messages, current_task=current_task,
        )
        messages[0] = {"role": "system", "content": SOLVER_TEXT_SYSTEM_PROMPT}
        messages[-1]["content"] = messages[-1]["content"].replace(
            "完成整个 Current Macro Task。current_task 必须填写其 id，并在 solution_draft 中给出完整论证。",
            "用自然语言完成整个 Current Macro Task，并给出完整论证。",
        ).replace(
            "只推进 Current Task 一个实质性步骤。current_task 字段请填写 Current Task 的 id。",
            "用自然语言只推进 Current Task 一个实质性步骤。",
        )
        messages[-1]["content"] += (
            "\n本次使用自然语言 Solver：上述字段仅供理解输入状态，"
            "不要按 JSON 字段回答，也不要为格式重写数学推导。"
        )
        self.last_solver_invalid = {}
        options = {}
        if self.thinking_mode != "default":
            options["thinking_mode"] = self.thinking_mode == "true"
        try:
            if state.efficient_runtime:
                state.model_call_count += 1
            response = call_model(
                self.client, state, debug_trace, "solver",
                messages=messages, temperature=0.2,
                max_tokens=int(getattr(self.config, "custom2_solver_max_tokens", 131072)),
                **options,
            )
            content = response.content.strip()
            self._remember_solver_response(content)
            if not content or response.finish_reason == "length":
                self.last_solver_invalid = {
                    "kind": "text_error", "task_id": current_task.id,
                    "error": "truncated_solver_text" if response.finish_reason == "length" else "empty_solver_text",
                }
                return None
            step = text_to_reasoning_step(content, state, current_task)
            debug_trace.append({
                "type": "solver_text_adapted", "task_id": current_task.id,
                "claim_count": len(step.new_results), "candidate_count": len(step.candidate_answers),
            })
            return step
        except Exception as exc:
            self.last_solver_invalid = {
                "kind": "chat_error", "task_id": current_task.id,
                "error": type(exc).__name__,
            }
            debug_trace.append({"type": "solver_text_error", "error_type": type(exc).__name__})
            return None


def text_to_reasoning_step(content: str, state: AgentState, current_task: Task) -> ReasoningStep:
    text = content.strip()
    if not text:
        raise ValueError("empty_solver_text")
    data = extract_json_object(text) if text.startswith(("{", "```json")) else None
    if data and data.get("type") == "reasoning_step":
        try:
            return ReasoningStep.model_validate(
                _normalize_reasoning_step_payload(data, state, current_task_id=current_task.id)
            )
        except ValueError:
            pass
    used_facts = [item.id for item in state.problem_facts if item.status == "verified"]
    used_definitions = [item.id for item in state.definitions if item.status == "verified"]
    used_results = [item.id for item in state.derived_results if item.status == "verified"]
    candidates = []
    markers = list(_CANDIDATE_MARKER.finditer(text))
    if len(markers) == 1:
        answer_text = text[markers[0].end():].strip()
        candidate = extract_candidate(create_draft("最终答案：\n" + answer_text, 1))
        if candidate is not None:
            candidates.append(candidate.value)
    result_type = {
        "compute": "equation", "case_analysis": "case_result",
        "lower_bound": "bound", "upper_bound": "bound",
        "construction": "construction", "completeness": "completeness",
    }.get(current_task.kind, "derived_fact")
    return ReasoningStep(
        type="reasoning_step", current_task=current_task.id,
        used_facts=used_facts, used_definitions=used_definitions, used_results=used_results,
        step_summary=f"当前任务的自然语言待审核草稿：{current_task.objective}",
        solution_draft=text,
        new_results=[ResultProposal(
            result_type=result_type, statement=text,
            justification="见本轮 solution_draft 的完整论证；由原审核流程判断是否成立。",
            depends_on=[*used_facts, *used_definitions, *used_results],
        )],
        candidate_answers=candidates, closed_tasks=[current_task.id], request_finalization=False,
    )


def format_solver_text_response(answer: str, problem: str) -> str:
    if answer.strip().lower() in {"", "unknown", "incomplete", "无法确定唯一答案"}:
        return "无法确定唯一答案"
    profile = infer_profile(problem)
    draft = create_draft(answer, 1, origin="finalizer")
    candidate = extract_candidate(draft)
    if candidate is None and profile.answer_mode != "proof":
        draft = create_draft("最终答案：\n" + answer, 1, origin="finalizer")
        candidate = extract_candidate(draft)
    return render_solution(draft, candidate, profile)
