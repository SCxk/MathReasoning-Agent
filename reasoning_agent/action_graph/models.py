from __future__ import annotations

from dataclasses import asdict, dataclass, field
import time
from typing import Any


@dataclass(frozen=True)
class SourceSpan:
    """半开区间，始终相对于不可变 raw_text 的 Python 字符偏移。"""

    start: int
    end: int
    text: str


@dataclass(frozen=True)
class ExtractedItem:
    kind: str
    value: str
    span: SourceSpan
    method: str = "regex"
    confidence: float = 1.0


@dataclass(frozen=True)
class Subquestion:
    id: str
    text: str
    span: SourceSpan
    target_type: str = "unknown"
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class FormulaRecord:
    raw: str
    normalized: str
    span: SourceSpan
    balanced: bool


@dataclass
class ProblemPacket:
    raw_text: str
    normalized_text: str
    normalized_to_raw: list[int]
    subquestions: list[Subquestion]
    formulas: list[FormulaRecord] = field(default_factory=list)
    numbers: list[ExtractedItem] = field(default_factory=list)
    conditions: list[ExtractedItem] = field(default_factory=list)
    domains: list[ExtractedItem] = field(default_factory=list)
    variables: list[ExtractedItem] = field(default_factory=list)
    targets: list[ExtractedItem] = field(default_factory=list)
    requirements_view: str = ""
    compact_view: str = ""
    compact_view_safe: bool = False
    complexity: str = "medium"
    complexity_signals: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def json_summary(self) -> dict[str, Any]:
        return {
            "raw_chars": len(self.raw_text), "normalized_chars": len(self.normalized_text),
            "subquestions": [asdict(item) for item in self.subquestions],
            "formula_count": len(self.formulas), "number_count": len(self.numbers),
            "condition_count": len(self.conditions), "domain_count": len(self.domains),
            "variable_count": len(self.variables), "target_count": len(self.targets),
            "compact_chars": len(self.compact_view), "compact_view_safe": self.compact_view_safe,
            "complexity": self.complexity, "signals": list(self.complexity_signals),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ActionDecision:
    action: str
    target_id: str
    goal: str
    required_fact_ids: tuple[str, ...] = ()
    success_condition: str = "给出可审核的局部结论"
    branch_hint: str | None = None


@dataclass
class AcceptedClaim:
    id: str
    text: str
    source_node_id: str
    dependencies: tuple[str, ...] = ()
    covered_subquestion_ids: tuple[str, ...] = ()
    audit_basis: str = ""
    valid: bool = True


@dataclass
class AnswerCandidate:
    id: str
    text: str
    answer_mode: str
    covered_subquestion_ids: tuple[str, ...]
    source_claim_ids: tuple[str, ...]
    source_node_id: str
    status: str = "pending"
    invalidation_reason: str = ""


@dataclass
class RouteFingerprint:
    action: str
    target_id: str
    reason: str
    assumptions: str = ""


@dataclass
class ActionNode:
    id: str
    decision: ActionDecision
    depth: int = 0
    parent_id: str | None = None
    attempts: int = 0
    output: str = ""
    status: str = "pending"


@dataclass
class RuntimeBudget:
    started_at: float
    deadline_at: float
    model_calls: int = 0
    planner_calls: int = 0
    executor_calls: int = 0
    reflector_calls: int = 0
    finalizer_calls: int = 0
    node_attempts: int = 0
    program_checks: int = 0
    repairs: int = 0
    network_recoveries: int = 0

    def remaining(self) -> float:
        return max(0.0, self.deadline_at - time.monotonic())


@dataclass
class ActionRuntimeState:
    problem_packet: ProblemPacket
    budget: RuntimeBudget
    nodes: dict[str, ActionNode] = field(default_factory=dict)
    frontier: list[str] = field(default_factory=list)
    accepted_claims: dict[str, AcceptedClaim] = field(default_factory=dict)
    answer_candidates: dict[str, AnswerCandidate] = field(default_factory=dict)
    rejected_routes: list[RouteFingerprint] = field(default_factory=list)
    subquestion_status: dict[str, str] = field(default_factory=dict)
    domain: str = "unknown"
    answer_mode: str = "other"
    risk_level: str = "medium"
    skill_domains: list[str] = field(default_factory=list)
    skill_sections: list[str] = field(default_factory=list)
    model_preprocess: str = ""
    profile_context: str = ""
    strategy_context: str = ""
    strategy_retrieval_text: str = ""
    strategy_results: list[dict[str, Any]] = field(default_factory=list)
    planner_strategy_cards: str = ""
    executor_strategy_cards: str = ""
    planner_strategy_cards_truncated: bool = False
    executor_strategy_cards_truncated: bool = False
    finalization_reason: str = ""

    def required_targets(self) -> set[str]:
        return set(self.subquestion_status)

    def supported_candidates(self) -> list[AnswerCandidate]:
        return [item for item in self.answer_candidates.values() if item.status == "supported"]

    def invalidate_claims(self, claim_ids: list[str], reason: str) -> None:
        invalid = set(claim_ids)
        changed = True
        while changed:
            changed = False
            for claim in self.accepted_claims.values():
                if claim.valid and any(dep in invalid for dep in claim.dependencies):
                    claim.valid = False
                    invalid.add(claim.id)
                    changed = True
        for candidate in self.answer_candidates.values():
            if candidate.status != "invalidated" and any(dep in invalid for dep in candidate.source_claim_ids):
                candidate.status = "invalidated"
                candidate.invalidation_reason = reason

    def refresh_candidates(self) -> None:
        targets = self.required_targets()
        for candidate in self.answer_candidates.values():
            if candidate.status == "invalidated":
                continue
            claims_ok = all(self.accepted_claims.get(cid) and self.accepted_claims[cid].valid for cid in candidate.source_claim_ids)
            coverage_ok = bool(candidate.covered_subquestion_ids) and set(candidate.covered_subquestion_ids).issubset(targets)
            candidate.status = "supported" if claims_ok and coverage_ok else "pending"
