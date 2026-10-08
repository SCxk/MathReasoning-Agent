from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _coerce_model_list(value: Any) -> list[Any]:
    """Accept a single JSON value where a model role omitted array brackets.

    Audit roles occasionally emit a valid failure report but serialize a
    one-item field such as ``required_changes`` as a string.  Treat that as a
    one-item list rather than discarding the entire report.  This changes only
    JSON shape recovery; the runtime still applies its evidence and quotation
    checks before a failure can trigger repair.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


class StagedStrategy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    problem_type: str = Field(default="unknown", max_length=120)
    risk_level: Literal["low", "medium", "high"] = "medium"
    main_method: str = Field(default="", max_length=2000)
    backup_method: str = Field(default="", max_length=2000)
    proof_obligations: list[str] = Field(default_factory=list, max_length=12)
    checks: list[str] = Field(default_factory=list, max_length=12)
    key_theorems: list[str] = Field(default_factory=list, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=12)
    # Model-selected retrieval targets.  These are identifiers only; the
    # runtime reads the corresponding local skill sections and never trusts
    # model-generated prose as a theorem.
    skill_domains: list[str] = Field(default_factory=list, max_length=2)
    skill_sections: list[str] = Field(default_factory=list, max_length=8)


class StagedAuditIssue(BaseModel):
    """An independent defect discovered while auditing a staged solution."""

    model_config = ConfigDict(extra="ignore")

    error_type: str = Field(default="other", max_length=120)
    invalid_claim: str = Field(default="", max_length=2000)
    evidence: str = Field(default="", max_length=3000)
    affected_reasoning: str = Field(default="", max_length=3000)
    required_changes: list[str] = Field(default_factory=list, max_length=12)
    forbidden_reuse: list[str] = Field(default_factory=list, max_length=12)
    prevention_rule: str = Field(default="", max_length=2000)

    @field_validator("required_changes", "forbidden_reuse", mode="before")
    @classmethod
    def coerce_list_fields(cls, value: Any) -> list[Any]:
        return _coerce_model_list(value)


class StagedAudit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verdict: Literal["pass", "fail", "uncertain"] = "uncertain"
    first_fatal_error: str = Field(default="", max_length=3000)
    evidence: str = Field(default="", max_length=3000)
    unmet_obligations: list[str] = Field(default_factory=list, max_length=12)
    repair_instruction: str = Field(default="", max_length=3000)
    error_type: str = Field(default="", max_length=120)
    invalid_claim: str = Field(default="", max_length=2000)
    counterexample_or_evidence: str = Field(default="", max_length=3000)
    required_changes: list[str] = Field(default_factory=list, max_length=12)
    forbidden_reuse: list[str] = Field(default_factory=list, max_length=12)
    replacement_route: str = Field(default="", max_length=2000)
    # The top-level fields identify the earliest root cause. This list records
    # defects that remain relevant after that root cause is fixed.
    additional_errors: list[StagedAuditIssue] = Field(default_factory=list, max_length=12)

    @field_validator(
        "unmet_obligations", "required_changes", "forbidden_reuse",
        "additional_errors", mode="before",
    )
    @classmethod
    def coerce_list_fields(cls, value: Any) -> list[Any]:
        return _coerce_model_list(value)


class StagedModelFidelity(BaseModel):
    """Whether the Solver's model preserves the problem's extracted constraints."""

    model_config = ConfigDict(extra="ignore")

    verdict: Literal["pass", "fail", "uncertain"] = "uncertain"
    first_fatal_error: str = Field(default="", max_length=3000)
    source_constraint: str = Field(default="", max_length=2000)
    solver_claim: str = Field(default="", max_length=2000)
    affected_reasoning: str = Field(default="", max_length=3000)
    required_changes: list[str] = Field(default_factory=list, max_length=12)
    additional_errors: list[StagedAuditIssue] = Field(default_factory=list, max_length=12)

    @field_validator("required_changes", "additional_errors", mode="before")
    @classmethod
    def coerce_list_fields(cls, value: Any) -> list[Any]:
        return _coerce_model_list(value)
