from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AnswerMode = Literal["choice", "judgment", "fill_blank", "computation", "proof", "other"]
Obligation = Literal[
    "answer_supported", "domain_conditions", "requested_parts", "proof_complete",
    "lower_bound", "upper_bound", "attaining_construction", "all_cases", "option_coverage",
]


class ControlMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProblemProfile(ControlMessage):
    domain: str = Field(default="unknown", max_length=80)
    answer_mode: AnswerMode = "other"
    obligations: list[Obligation] = Field(default_factory=list, max_length=10)


class ObligationCheck(ControlMessage):
    obligation: Obligation
    status: Literal["supported", "missing", "contradicted"]
    evidence_ids: list[str] = Field(default_factory=list, max_length=32)


class AuditIssue(ControlMessage):
    location: str = Field(min_length=1, max_length=40)
    kind: Literal[
        "arithmetic", "invalid_assumption", "missing_proof", "missing_construction",
        "case_coverage", "domain", "answer_mismatch", "other",
    ]
    quote: str = Field(min_length=1, max_length=2000)
    reason: str = Field(min_length=1, max_length=2000)


class DraftAudit(ControlMessage):
    solution_id: str = Field(min_length=1, max_length=32)
    verdict: Literal["accept", "repair", "reject_route", "uncertain"]
    answer_status: Literal["supported", "unsupported", "contradicted"]
    obligation_checks: list[ObligationCheck] = Field(max_length=10)
    issues: list[AuditIssue] = Field(default_factory=list, max_length=16)


class AnswerExtraction(ControlMessage):
    solution_id: str = Field(min_length=1, max_length=32)
    paragraph_id: str = Field(min_length=1, max_length=40)
    answer: str = Field(min_length=1, max_length=16000)


@dataclass(frozen=True)
class Paragraph:
    id: str
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class SolutionDraft:
    id: str
    text: str
    paragraphs: tuple[Paragraph, ...]
    parent_id: str | None = None
    origin: str = "solver"
    truncated: bool = False
    task_id: str | None = None


@dataclass(frozen=True)
class TextCandidate:
    id: str
    solution_id: str
    value: str
    start: int
    end: int
    source: str


@dataclass(frozen=True)
class NarrativeAudit:
    solution_id: str
    verdict: Literal["accept", "repair", "reject_route", "uncertain"]
    feedback: str
    routing_status: str


@dataclass(frozen=True)
class AuditRecord:
    id: str
    solution_id: str
    review: DraftAudit | NarrativeAudit
