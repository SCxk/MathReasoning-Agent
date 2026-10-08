import json
import re

from reasoning_agent.custom2.models import AgentState, CandidateAnswer, StrategyGuidance, Task
from reasoning_agent.custom2.prompts import (
    CANDIDATE_SET_VERIFIER_PROMPT,
    CANDIDATE_VERIFIER_PROMPT,
    EMERGENCY_FINALIZER_PROMPT,
    FINALIZER_PROMPT,
    CRITIQUE_SYSTEM_PROMPT,
    REPAIR_SYSTEM_PROMPT,
    SOLVER_SYSTEM_PROMPT,
    STEP_VERIFIER_SYSTEM_PROMPT,
)
from reasoning_agent.custom2.schemas import CritiqueOutput, ReasoningStep, SolutionDraft
from reasoning_agent.custom2.state_manager import (
    choose_active_task,
    choose_open_task,
    remaining_seconds,
)


def build_solver_messages(
    state: AgentState,
    history_messages: list[dict] | None = None,
    current_task: Task | None = None,
) -> list[dict]:
    history = [] if state.efficient_runtime else list(history_messages or [])
    return [
        {"role": "system", "content": SOLVER_SYSTEM_PROMPT},
        *history,
        build_runtime_state_message(state, current_task=current_task),
    ]


def build_runtime_state_message(
    state: AgentState,
    current_task: Task | None = None,
) -> dict:
    return {"role": "user", "content": render_solver_context(state, current_task)}


def render_solver_context(
    state: AgentState,
    current_task: Task | None = None,
) -> str:
    current_task = current_task or choose_active_task(state) or choose_open_task(state)
    if state.efficient_runtime:
        return _render_efficient_solver_context(state, current_task)
    route_pressure = _render_route_pressure(state, current_task)
    return f"""## Problem
{state.problem}

## Problem Type
{state.problem_type}

## VERIFIED Problem Facts
{_render_items([pf for pf in state.problem_facts if pf.status == "verified"])}

## VERIFIED Definitions
{_render_items([d for d in state.definitions if d.status == "verified"])}

## VERIFIED Derived Results
{_render_items([r for r in state.derived_results if r.status == "verified"])}

## Candidates
{_render_items(state.candidates)}

## Completion Requirements
{_render_items(state.requirements)}

## Strategy Guidance
{_render_strategy_guidance(state)}

## Dynamic Tasks
{_render_items([task for task in state.tasks if task.status in {"open", "active", "blocked"}])}

## Current Task
{_render_items([current_task] if current_task else [])}

## Active Branch
{state.active_branch_id or ""}

## Route Pressure
{route_pressure}

## Relevant Failed Approaches
{_render_items(state.error_memory[-6:])}

## Budget
Solver calls: {state.solver_call_count}/{state.max_solver_calls}
Accepted steps: {state.accepted_step_count}/{state.max_accepted_steps}
Local retries: {state.local_retry_count}/{state.max_local_retries}

只推进 Current Task 一个实质性步骤。current_task 字段请填写 Current Task 的 id。
"""


def build_critique_messages(
    state: AgentState, step: ReasoningStep, draft: SolutionDraft
) -> list[dict]:
    claims = "\n".join(
        f"- {claim.id} [{claim.claim_type}] {claim.statement} dependencies={claim.depends_on}"
        for claim in draft.claims
    ) or "(none)"
    content = f"""## Problem
{state.problem}

## Recent Failed Routes (mandatory constraints)
{_render_items([
    {
        "id": error.id,
        "category": error.category,
        "step_summary": error.step_summary,
        "reason": error.reason,
        "retry_instruction": error.retry_instruction,
    }
    for error in state.error_memory[-6:]
])}

## Failed Route Fingerprints
{_render_items(state.failed_route_fingerprints[-3:])}

## Verified Facts
{_render_items([pf for pf in state.problem_facts if pf.status == "verified"])}

## Verified Results
{_render_items([result for result in state.derived_results if result.status == "verified"][-12:])}

## Current Task
{draft.task_id}

## Solution Draft v{draft.version}
{draft.text}

## Claims
{claims}

## Candidate Answers
{_render_items(draft.candidate_answers)}
"""
    return [
        {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
        {"role": "user", "content": _truncate(content, state.solver_context_max_chars)},
    ]


def build_repair_messages(
    state: AgentState,
    step: ReasoningStep,
    draft: SolutionDraft,
    critique: CritiqueOutput,
) -> list[dict]:
    accepted = set(critique.accepted_claims)
    kept = [claim for claim in draft.claims if claim.id in accepted]
    invalid = [claim for claim in draft.claims if claim.id in set(critique.invalid_claims)]
    content = f"""## Problem
{state.problem}

## Current Task
{draft.task_id}

## Current Solution Draft v{draft.version}
{draft.text}

## Safe Claims To Keep
{_render_items(kept)}

## Invalid Claims To Repair
{_render_items(invalid)}

## Minimal Repair Instruction
{critique.repair_instruction or critique.reason}

## Output Contract
Return ReasoningStep JSON for current_task={draft.task_id}. Include the repaired complete solution_draft.
"""
    return [
        {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
        {"role": "user", "content": _truncate(content, state.solver_context_max_chars)},
    ]


def build_step_verifier_messages(state: AgentState, step: ReasoningStep) -> list[dict]:
    return [
        {"role": "system", "content": STEP_VERIFIER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "problem": state.problem,
                    "verified_problem_facts": [
                        pf.model_dump() for pf in state.problem_facts if pf.status == "verified"
                    ],
                    "verified_definitions": [
                        d.model_dump() for d in state.definitions if d.status == "verified"
                    ],
                    "verified_results": [
                        r.model_dump() for r in state.derived_results if r.status == "verified"
                    ],
                    "completion_requirements": [
                        req.model_dump() for req in state.requirements
                    ],
                    "choice_options": _extract_choice_options(state.problem),
                    "tasks": [task.model_dump() for task in state.tasks],
                    "recent_failed_approaches": [
                        {
                            "id": err.id,
                            "branch_id": err.branch_id,
                            "category": err.category,
                            "step_summary": err.step_summary,
                            "reason": err.reason,
                            "retry_instruction": err.retry_instruction,
                            "related_ids": err.related_ids,
                        }
                        for err in state.error_memory[-6:]
                    ],
                    "candidate_step": step.model_dump(),
                },
                ensure_ascii=False,
            ),
        },
    ]


def build_candidate_verifier_messages(
    state: AgentState, candidate: CandidateAnswer
) -> list[dict]:
    return [
        {"role": "system", "content": CANDIDATE_VERIFIER_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "problem": state.problem,
                    "candidate": candidate.model_dump(),
                    "verified_definitions": [
                        d.model_dump() for d in state.definitions if d.status == "verified"
                    ],
                    "verified_results": [
                        r.model_dump() for r in state.derived_results if r.status == "verified"
                    ],
                    "solver_route": {
                        "source_draft_version": candidate.source_draft_version,
                        "solution_draft": candidate.source_solution_draft,
                        "strategy_methods": candidate.source_strategy_methods,
                    },
                    "required_verification_mode": (
                        "Do not merely restate solver_route. Use a different representation, "
                        "direct substitution, boundary/counterexample search, or small-case enumeration."
                    ),
                    "all_candidates": [c.model_dump() for c in state.candidates],
                    "candidate_set_verifications": [
                        record.model_dump()
                        for record in state.candidate_set_verifications[-3:]
                    ],
                    "recent_failed_approaches": [
                        {
                            "id": err.id,
                            "category": err.category,
                            "step_summary": err.step_summary,
                            "reason": err.reason,
                            "retry_instruction": err.retry_instruction,
                            "related_ids": err.related_ids,
                        }
                        for err in state.error_memory[-6:]
                    ],
                    "completion_requirements": [
                        req.model_dump() for req in state.requirements
                    ],
                    "choice_options": _extract_choice_options(state.problem),
                    "domain_constraints": [
                        pf.model_dump()
                        for pf in state.problem_facts
                        if pf.status == "verified" and pf.fact_type == "domain_constraint"
                    ],
                },
                ensure_ascii=False,
            ),
        },
    ]


def build_candidate_set_verifier_messages(state: AgentState) -> list[dict]:
    return [
        {"role": "system", "content": CANDIDATE_SET_VERIFIER_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "problem": state.problem,
                    "problem_type": state.problem_type,
                    "all_candidates": [candidate.model_dump() for candidate in state.candidates],
                    "candidate_verifications": [
                        record.model_dump() for record in state.candidate_verifications
                    ],
                    "verified_definitions": [
                        item.model_dump()
                        for item in state.definitions
                        if item.status == "verified"
                    ],
                    "verified_results": [
                        item.model_dump()
                        for item in state.derived_results
                        if item.status == "verified"
                    ],
                    "completion_requirements": [
                        requirement.model_dump() for requirement in state.requirements
                    ],
                    "domain_constraints": [
                        fact.model_dump()
                        for fact in state.problem_facts
                        if fact.status == "verified"
                        and fact.fact_type == "domain_constraint"
                    ],
                    "choice_options": _extract_choice_options(state.problem),
                },
                ensure_ascii=False,
            ),
        },
    ]


def build_finalizer_messages(
    state: AgentState,
    solver_history_messages: list[dict] | None = None,
    unparsed_solver_responses: list[str] | None = None,
    emergency: bool = False,
    best_effort_verification: dict | None = None,
) -> list[dict]:
    prompt = EMERGENCY_FINALIZER_PROMPT if emergency else FINALIZER_PROMPT
    history = [] if state.efficient_runtime else list(solver_history_messages or [])[-12:]
    return [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "problem": state.problem,
                    "problem_facts": [
                        pf.model_dump() for pf in state.problem_facts if pf.status == "verified"
                    ],
                    "definitions": [
                        d.model_dump() for d in state.definitions if d.status == "verified"
                    ],
                    "derived_results": [
                        r.model_dump() for r in state.derived_results if r.status == "verified"
                    ],
                    "verified_candidates": [
                        c.model_dump() for c in state.candidates if c.status == "verified"
                    ],
                    "all_candidates": [c.model_dump() for c in state.candidates],
                    "candidate_set_verifications": [
                        record.model_dump()
                        for record in state.candidate_set_verifications[-3:]
                    ],
                    "completion_requirements": [
                        req.model_dump()
                        for req in state.requirements
                    ],
                    "choice_options": _extract_choice_options(state.problem),
                    "tasks": [task.model_dump() for task in state.tasks],
                    "error_memory": [err.model_dump() for err in state.error_memory[-10:]],
                    "progress_audits": [
                        audit.model_dump() for audit in state.progress_audits[-10:]
                    ],
                    "replan_records": [
                        record.model_dump() for record in state.replan_records[-10:]
                    ],
                    "solution_draft": state.solution_draft.model_dump(),
                    "accepted_claims": [claim.model_dump() for claim in state.accepted_claims],
                    "finalize_mode": state.finalize_mode,
                    "finalize_reason": state.finalize_reason,
                    "best_effort_verification": best_effort_verification,
                    "solver_history_messages": history,
                    "unparsed_solver_responses": [
                        str(item)[-12000:]
                        for item in (unparsed_solver_responses or [])[-3:]
                    ],
                    "route_pressure": {
                        "solver_call_count": state.solver_call_count,
                        "accepted_step_count": state.accepted_step_count,
                        "local_retry_count": state.local_retry_count,
                        "strategy_reset_count": state.strategy_reset_count,
                        "max_solver_calls": state.max_solver_calls,
                        "max_accepted_steps": state.max_accepted_steps,
                        "max_local_retries": state.max_local_retries,
                        "max_strategy_resets": state.max_strategy_resets,
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]


def _render_efficient_solver_context(
    state: AgentState, current_task: Task | None
) -> str:
    content = f"""## Problem
{state.problem}

## Domain
primary={state.problem_type}; secondary={state.secondary_problem_types}

## Strategy Guidance
{_render_strategy_guidance(state)}

## Execution Mode
{state.execution_mode}

## Current Macro Task
{_render_items([current_task] if current_task else [])}

## Reliable Problem Facts
{_render_items([pf for pf in state.problem_facts if pf.status == "verified"][-16:])}

## Reliable Conclusions
{_render_items([result for result in state.derived_results if result.status == "verified"][-12:])}

## Current Solution Draft
{state.solution_draft.text or "(none)"}

## Current Candidates
{_render_items([candidate for candidate in state.candidates if candidate.status != "rejected"][-6:])}

## Recent Failed Routes
{_render_items(state.failed_route_fingerprints[-3:])}

## Recent Detailed Error Memory
{_render_items(state.error_memory[-4:])}

## Budget Summary
solver_calls={state.solver_call_count}/{state.max_solver_calls}; repairs={state.repair_count}/{state.max_repairs}; replans={state.model_replan_count}/{state.max_model_replans}; remaining_seconds={remaining_seconds(state):.1f}

完成整个 Current Macro Task。current_task 必须填写其 id，并在 solution_draft 中给出完整论证。
"""
    return _truncate(content, state.solver_context_max_chars)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 40)] + "\n...[context truncated by runtime]"


def _render_items(items: list[object]) -> str:
    if not items:
        return "(none)"
    rendered = []
    for item in items:
        if hasattr(item, "model_dump"):
            rendered.append(json.dumps(item.model_dump(), ensure_ascii=False))
        else:
            rendered.append(str(item))
    return "\n".join(rendered)


def _render_strategy_guidance(state: AgentState) -> str:
    active = [item for item in state.strategy_guidance if item.status == "active"]
    if not active:
        return "(none)"
    guidance: StrategyGuidance = active[-1]
    return json.dumps(
        {
            "id": guidance.id,
            "problem_type": guidance.problem_type,
            "core_methods": guidance.core_methods,
            "phase_plan": guidance.phase_plan,
            "risk_controls": guidance.risk_controls,
            "do_not": guidance.do_not,
            "first_step_instruction": guidance.first_step_instruction,
            "note": (
                "Strategy Guidance 只是未证明的路线建议；不能作为 P/D/R/C 证据，"
                "如果与 verified state 冲突，必须以 verified state 为准。"
            ),
        },
        ensure_ascii=False,
    )


def _render_route_pressure(state: AgentState, current_task: Task | None) -> str:
    if current_task is None:
        return "(none)"
    lines = [
        f"current_task={current_task.id}",
        f"kind={current_task.kind}",
        f"math_rejects={current_task.math_rejects}",
        f"protocol_failures={current_task.protocol_failures}",
    ]
    if current_task.math_rejects >= 2 or current_task.protocol_failures >= 2:
        lines.append("当前路线已连续失败两次，下一步必须切换方法，不能继续补洞。")
        lines.append("可选模式：继续证明 / 枚举反例 / 改换分类/构造路线。")
    return "\n".join(lines)


def _extract_choice_options(problem: str) -> list[str]:
    text = problem.replace("\r", "\n")
    matches = list(re.finditer(r"(?<![A-Z])([A-H])[\.\、\)]\s*", text))
    if not matches:
        return []

    options: list[str] = []
    for index, match in enumerate(matches):
        label = match.group(1)
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[content_start:content_end].strip(" \n\t；;。")
        if not content:
            continue
        options.append(f"{label}. {content}")
    return options
