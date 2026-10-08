"""LangGraph routing with atomic, task-store-owned stage checkpoints."""

import asyncio
import copy
import hashlib
import json
import threading
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.errors import NodeCancelledError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from agent_platform.runtime import CheckpointIncompatible, RuntimeContext, RuntimeResult, STAGES, ModelPermits
from agent_platform.safety import sanitize
from agent_platform.presentation import RESOLVED_STYLES, requested_style
from agent_platform.staged_adapter import ExecutionStopped, StagedAdapter
from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom2.staged_models import StagedAudit, StagedStrategy
from reasoning_agent.custom2.text_models import ProblemProfile
from agent_platform.tools.registry import ToolRegistry
from agent_platform.tools.schemas import Passage


WORKFLOW_VERSION = "staged-graph-v4"


class GraphState(TypedDict, total=False):
    schema_version: str
    task_id: str
    session_id: str
    problem_hash: str
    config_hash: str
    deadline_at: str
    profile: dict[str, Any]
    plan: dict[str, Any]
    adapter: dict[str, Any]
    draft: str
    checks: dict[str, Any]
    verification: dict[str, Any]
    repair_count: int
    max_repairs: int
    solve_calls_used: int
    max_solve_calls: int
    recoverable_error: str
    next_stage: str
    final_response: str
    response_style: str | None
    evidence: list[dict[str, Any]]


class GraphCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: str
    task_id: str
    session_id: str
    problem_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    deadline_at: str
    profile: ProblemProfile | None = None
    plan: StagedStrategy | None = None
    adapter: dict[str, Any]
    draft: str = Field(default="", max_length=48000)
    checks: dict[str, Any] = Field(default_factory=dict)
    verification: StagedAudit | None = None
    repair_count: int = Field(ge=0, le=3)
    max_repairs: int = Field(ge=0, le=3)
    solve_calls_used: int = Field(ge=0, le=4)
    max_solve_calls: int = Field(ge=1, le=4)
    recoverable_error: str
    next_stage: str
    final_response: str = ""
    response_style: Literal["auto", "answer", "brief", "detailed"] | None = None
    evidence: list[Passage] = Field(default_factory=list, max_length=5)

    @field_validator("deadline_at")
    @classmethod
    def valid_deadline(cls, value):
        if datetime.fromisoformat(value).tzinfo is None:
            raise ValueError("timezone_required")
        return value


def route(stage: str, state: GraphState, *, budget_available: bool) -> str:
    if stage == "finalize":
        return "terminal"
    if not budget_available:
        return "finalize"
    if stage in {"solve", "repair"}:
        return "tool" if state.get("draft") and not state.get("recoverable_error") else "finalize"
    if stage == "verify":
        audit = state["verification"]
        if (audit["verdict"] == "fail" and audit.get("first_fatal_error", "").strip()
                and state["repair_count"] < state["max_repairs"]
                and state["solve_calls_used"] < state["max_solve_calls"]):
            return "repair"
        return "finalize"
    return {"profile": "retrieve", "retrieve": "plan", "plan": "solve", "tool": "verify"}[stage]


class LangGraphRuntime:
    name = "langgraph_staged"

    def __init__(self, client: Any, config: AgentConfig | None = None,
                 *, model_concurrency: int = 8, client_identity: str | None = None,
                 adapter_factory=StagedAdapter, tools: ToolRegistry | None = None,
                 function_calling: str = "auto") -> None:
        if client is None or not callable(getattr(client, "chat", None)):
            raise ValueError("injected_client_required")
        if model_concurrency < 1:
            raise ValueError("invalid_model_concurrency")
        self.client = client
        self.config = copy.deepcopy(config or AgentConfig(custom2_solver_protocol="staged"))
        self.permits: ModelPermits = threading.BoundedSemaphore(model_concurrency)
        self.adapter_factory = adapter_factory
        if function_calling not in {"auto", "native", "json", "off"}:
            raise ValueError("invalid_function_calling_mode")
        self.tools = tools or ToolRegistry()
        self.function_calling = function_calling
        # Refuse incompatible code/prompt/config checkpoints instead of guessing.
        source_root = Path(__file__).resolve().parent.parent
        digest = hashlib.sha256(json.dumps(asdict(self.config), sort_keys=True).encode())
        identity = client_identity or f"{type(client).__module__}.{type(client).__qualname__}"
        digest.update(identity.encode())
        digest.update(f"{self.tools.identity}:{function_calling}".encode())
        for folder in ("agent_platform", "reasoning_agent/custom2", "reasoning_agent/custom"):
            for path in sorted((source_root / folder).rglob("*.py")):
                digest.update(path.relative_to(source_root).as_posix().encode())
                digest.update(path.read_bytes())
        self.config_hash = digest.hexdigest()

    def checkpoint_compatible(self, checkpoint: dict | None) -> bool:
        if checkpoint is None:
            return True
        try:
            parsed = GraphCheckpoint.model_validate(checkpoint)
        except ValidationError:
            return False
        effective = parsed.adapter.get("_response_style")
        if parsed.response_style == "auto":
            if not isinstance(effective, str) or effective not in RESOLVED_STYLES:
                return False
        elif effective != parsed.response_style:
            return False
        if parsed.next_stage in {"retrieve", "plan", "solve", "tool", "verify", "repair"} and parsed.profile is None:
            return False
        if parsed.next_stage in {"solve", "tool", "verify", "repair"} and parsed.plan is None:
            return False
        if parsed.next_stage in {"tool", "verify", "repair"} and not parsed.draft:
            return False
        if parsed.next_stage == "verify" and not isinstance(parsed.checks.get("ok"), bool):
            return False
        if parsed.next_stage == "repair" and parsed.verification is None:
            return False
        if parsed.next_stage == "terminal" and not parsed.final_response.strip():
            return False
        return (parsed.schema_version == WORKFLOW_VERSION
                and parsed.config_hash == self.config_hash
                and parsed.next_stage in {*STAGES, "terminal"}
                and parsed.repair_count <= parsed.max_repairs
                and parsed.solve_calls_used <= parsed.max_solve_calls)

    def _load(self, context: RuntimeContext) -> GraphState:
        if not context.deadline_at:
            context.deadline_at = datetime.now(timezone.utc) + timedelta(seconds=1200)
        problem_hash = hashlib.sha256(context.problem.encode()).hexdigest()
        if context.checkpoint is not None:
            state = copy.deepcopy(context.checkpoint)
            if (not self.checkpoint_compatible(state)
                    or state.get("task_id") != context.task_id
                    or state.get("session_id") != context.session_id
                    or state.get("problem_hash") != problem_hash
                    or state.get("response_style") != requested_style(context.metadata)
                    or state.get("deadline_at") != context.deadline_at.isoformat()):
                raise CheckpointIncompatible("checkpoint_incompatible")
            return state
        max_repairs = min(3, max(0, int(self.config.custom2_max_repairs)))
        return {
            "schema_version": WORKFLOW_VERSION, "task_id": context.task_id,
            "session_id": context.session_id, "problem_hash": problem_hash,
            "config_hash": self.config_hash, "deadline_at": context.deadline_at.isoformat(),
            "repair_count": 0, "max_repairs": max_repairs, "solve_calls_used": 0,
            "max_solve_calls": max_repairs + 1, "next_stage": "profile",
            "adapter": {}, "recoverable_error": "",
            "response_style": requested_style(context.metadata),
        }

    def _budget_available(self, context):
        return (context.deadline_at - datetime.now(timezone.utc)).total_seconds() > context.finalize_reserve_seconds

    async def run(self, context: RuntimeContext) -> RuntimeResult:
        if context.finalize_reserve_seconds < 25:
            raise ValueError("graph_requires_finalize_reserve")
        state = self._load(context)
        context.tools = self.tools
        context.function_calling = self.function_calling
        context.max_solve_calls = state["max_solve_calls"]
        context.solver_calls_used = max(context.solver_calls_used, state["solve_calls_used"])
        state["solve_calls_used"] = context.solver_calls_used
        if state.get("adapter", {}).get("_best_candidate_draft"):
            adapter = self.adapter_factory(self.client, self.config, context, "finalize", self.permits, state)
            context.save_response(adapter._saved_candidate_answer())
        if state["next_stage"] == "terminal":
            return RuntimeResult(state["final_response"])
        graph = StateGraph(GraphState)

        def node(stage):
            async def execute(current):
                if context.cancelled.is_set():
                    raise asyncio.CancelledError
                context.progress(stage)
                adapter = self.adapter_factory(self.client, self.config, context, stage, self.permits, current)
                try:
                    updates = await asyncio.to_thread(adapter.execute, copy.deepcopy(current))
                except ExecutionStopped:
                    raise asyncio.CancelledError from None
                except Exception:
                    # Store/lease errors must escape; recording also fences the owner.
                    context.record(stage, "stage.recovered_error", {"error_code": "stage_failed"})
                    if not current.get("adapter", {}).get("_best_candidate_draft"):
                        raise
                    updates = {"recoverable_error": "stage_failed", "next_stage": "finalize"}
                updated = {**current, **updates}
                updated["solve_calls_used"] = context.solver_calls_used
                updated["next_stage"] = (
                    "finalize" if updates.get("next_stage") == "finalize"
                    else route(stage, updated, budget_available=self._budget_available(context))
                )
                updated = sanitize(updated)
                json.dumps(updated, allow_nan=False)
                context.progress(stage, completed=True, checkpoint=updated)
                context.checkpoint = updated
                if updated.get("adapter", {}).get("_best_candidate_draft"):
                    context.save_response(adapter._saved_candidate_answer())
                return updated
            return execute

        for stage in STAGES:
            graph.add_node(stage, node(stage))
            graph.add_conditional_edges(stage, lambda value: value["next_stage"],
                                        {**{name: name for name in STAGES}, "terminal": END})
        graph.add_conditional_edges(START, lambda value: (
            value["next_stage"] if self._budget_available(context) else "finalize"
        ), {stage: stage for stage in STAGES})
        try:
            output = await graph.compile().ainvoke(state, {"recursion_limit": 40})
            return RuntimeResult(output["final_response"])
        except NodeCancelledError:
            raise asyncio.CancelledError from None
        finally:
            context.cancelled.set()
