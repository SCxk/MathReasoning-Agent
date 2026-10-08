"""One policy boundary for local, native function-call and MCP execution."""

import asyncio
import copy
import hashlib
import json
import time
import threading
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError

from agent_platform.safety import sanitize
from agent_platform.tools.schemas import ARGUMENTS, VALUES, SCHEMA_VERSION, ToolInvocation, ToolResult


MAX_RESULT_BYTES = 65536


def failure(code, *, retryable=False):
    return ToolResult(status="failed", error_code=code, retryable=retryable)


def fingerprint(name, arguments):
    return hashlib.sha256(json.dumps([name, arguments], sort_keys=True,
                                    allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def stable_call_id(context, stage, slot, name, arguments):
    return str(uuid5(NAMESPACE_URL, f"{context.task_id}:{stage}:{slot}:{fingerprint(name, arguments)}"))


def validated_result(name, raw):
    if len(json.dumps(raw, allow_nan=False).encode()) > MAX_RESULT_BYTES:
        raise ValueError("oversized_result")
    result = ToolResult.model_validate(raw)
    if result.value is not None:
        result.value = VALUES[name].model_validate(result.value).model_dump()
    result = ToolResult.model_validate(sanitize(result.model_dump()))
    if result.value is not None:
        VALUES[name].model_validate(result.value)
    return result


class ToolRegistry:
    def __init__(self, local=None, *, mcp=None, mcp_tools=("strategy_search", "math_verify"),
                 equivalent_fallback=True):
        if local is None:
            from agent_platform.tools.local import LocalTools
            local = LocalTools()
        self.local, self.mcp = local, mcp
        self.mcp_tools = frozenset(mcp_tools)
        if not self.mcp_tools <= {"strategy_search", "math_verify"}:
            raise ValueError("unsupported_mcp_tool")
        self.equivalent_fallback = equivalent_fallback

    @property
    def identity(self):
        documents = getattr(self.local, "documents", None)
        rag = documents.identity if documents is not None else "rag-disabled"
        return f"{SCHEMA_VERSION}:{'mcp' if self.mcp else 'local'}:{sorted(self.mcp_tools)}:{self.equivalent_fallback}:{rag}"

    async def invoke(self, request: ToolInvocation, context):
        if request.call_id not in context.tool_locks and len(context.tool_locks) >= 64:
            return failure("budget_exhausted")
        lock = context.tool_locks.setdefault(request.call_id, threading.Lock())
        while not lock.acquire(blocking=False):
            self._running(context)
            await asyncio.sleep(.01)
        try:
            return await self._invoke(request, context)
        finally:
            lock.release()

    async def _invoke(self, request: ToolInvocation, context):
        if request.task_id != context.task_id:
            return failure("scope_violation")
        name = request.tool_name
        # Invalid requests are traced but never saved as executable inputs.
        if name not in ARGUMENTS:
            context.record(request.stage_id, "tool.rejected", {"error_code": "unknown_tool"})
            return failure("unknown_tool")
        try:
            args = ARGUMENTS[name].model_validate(request.arguments).model_dump()
        except ValidationError:
            context.record(request.stage_id, "tool.rejected", {"name": name, "error_code": "invalid_arguments"})
            return failure("invalid_arguments")
        if name == "document_search" and args["session_id"] != context.session_id:
            context.record(request.stage_id, "tool.rejected", {"name": name, "error_code": "scope_violation"})
            return failure("scope_violation")
        if name == "document_search" and "document_ids" in context.metadata:
            selected = context.metadata["document_ids"]
            requested = args["document_ids"]
            if requested is not None and not set(requested).issubset(selected):
                context.record(request.stage_id, "tool.rejected", {"name": name, "error_code": "scope_violation"})
                return failure("scope_violation")
            args["document_ids"] = selected if requested is None else requested
        digest = fingerprint(name, args)
        entry = copy.deepcopy(context.tool_calls.get(request.call_id))
        if entry and (entry["arguments_hash"] != digest or entry["stage_id"] != request.stage_id):
            return failure("idempotency_conflict")
        if entry and entry.get("result"):
            context.record(request.stage_id, "tool.replayed", {"name": name, "call_id": request.call_id})
            return validated_result(name, entry["result"])
        transport = "mcp" if self.mcp and name in self.mcp_tools else "local"
        if entry is None:
            if len(context.tool_calls) >= 64:
                return failure("budget_exhausted")
            entry = {"schema_version": SCHEMA_VERSION, "tool_name": name,
                     "stage_id": request.stage_id, "arguments_hash": digest,
                     "arguments_summary": {key: {"characters": len(value)} if isinstance(value, str) else value
                                           for key, value in args.items()},
                     "transport": transport, "timeout_ms": request.timeout_ms,
                     "status": "started", "attempts": [], "result": None}
        # A crash consumes its started attempt; never reset the retry budget.
        for item in entry["attempts"]:
            if item["status"] == "started":
                item.update(status="interrupted", error_code="transport_error", retryable=True)
        result = failure("retry_exhausted")
        for number in range(len(entry["attempts"]), 3):
            self._running(context)
            remaining = self._remaining(context)
            seconds = request.timeout_ms / 1000
            if remaining < seconds:
                result = failure("budget_exhausted")
                break
            attempt_id = str(uuid5(NAMESPACE_URL, f"{request.call_id}:{number}"))
            item = {"id": attempt_id, "attempt": number, "status": "started",
                    "started_at": datetime.now(timezone.utc).isoformat()}
            entry["attempts"].append(item)
            context.commit_tool(request.call_id, copy.deepcopy(entry), "tool.started", {
                "name": name, "call_id": request.call_id, "operation_id": attempt_id,
                "transport": transport, "attempt": number, "arguments_hash": digest,
            })
            started = time.monotonic()
            try:
                target = self.mcp if transport == "mcp" else self.local
                raw = await self._bounded(target.invoke(name, args), seconds, context)
                result = validated_result(name, raw)
            except TimeoutError:
                result = failure("timeout", retryable=transport == "mcp")
            except (ValidationError, ValueError, TypeError):
                result = failure("invalid_result")
            except Exception:
                result = failure("transport_error" if transport == "mcp" else "execution_error",
                                 retryable=transport == "mcp")
            self._running(context)
            result.latency_ms = max(0, int((time.monotonic() - started) * 1000))
            # Only declared temporary failures can authorize another attempt.
            result.retryable = (result.retryable and result.error_code in {"timeout", "transport_error"}
                                and (transport == "mcp" or name == "sympy_calculate"))
            item.update(status="succeeded" if result.status != "failed" else "failed",
                        latency_ms=result.latency_ms, error_code=result.error_code,
                        retryable=result.retryable, finished_at=datetime.now(timezone.utc).isoformat())
            if not result.retryable:
                entry.update(status=result.status, result=result.model_dump())
            context.commit_tool(request.call_id, copy.deepcopy(entry),
                                "tool.completed" if result.status != "failed" else "tool.failed", {
                "name": name, "call_id": request.call_id, "operation_id": attempt_id,
                "attempt": number, "status": result.status, "error_code": result.error_code,
                "retryable": result.retryable, "latency_ms": result.latency_ms,
                "citations": result.citations,
                **({"verdict": result.value["verdict"]} if name == "math_verify" and result.value else {}),
            })
            if not result.retryable:
                break
        if (result.status == "failed" and result.error_code in {"timeout", "transport_error", "retry_exhausted"}
                and transport == "mcp" and self.equivalent_fallback
                and not entry.get("fallback_started")
                and self._remaining(context) >= request.timeout_ms / 1000):
            self._running(context)
            fallback_id = f"{request.call_id}:local"
            entry["fallback_started"] = True
            context.commit_tool(request.call_id, copy.deepcopy(entry), "tool_fallback.started", {
                "name": name, "call_id": request.call_id, "operation_id": fallback_id})
            try:
                result = validated_result(name, await self._bounded(
                    self.local.invoke(name, args), request.timeout_ms / 1000, context))
                if result.status == "succeeded":
                    result.status = "fallback"
            except Exception:
                result = failure("execution_error")
            self._running(context)
            entry.update(status=result.status, result=result.model_dump())
            context.commit_tool(request.call_id, copy.deepcopy(entry), "tool_fallback.completed", {
                "name": name, "call_id": request.call_id, "operation_id": fallback_id,
                "status": result.status, "error_code": result.error_code})
        if result.retryable:
            result = failure("retry_exhausted")
        entry.update(status=result.status, result=result.model_dump())
        context.commit_tool(request.call_id, copy.deepcopy(entry), "tool.committed", {
            "name": name, "call_id": request.call_id, "status": result.status,
            "retry_count": max(0, len(entry["attempts"]) - 1), "error_code": result.error_code,
        })
        return result

    @staticmethod
    async def _bounded(awaitable, seconds, context):
        work = asyncio.create_task(awaitable)
        deadline = time.monotonic() + seconds
        try:
            while not work.done():
                ToolRegistry._running(context)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                await asyncio.wait({work}, timeout=min(.05, remaining))
            return await work
        finally:
            if not work.done():
                work.cancel()
            await asyncio.gather(work, return_exceptions=True)

    @staticmethod
    def _remaining(context):
        if context.deadline_at is None:
            return float("inf")
        return (context.deadline_at - datetime.now(timezone.utc)).total_seconds() - context.finalize_reserve_seconds

    @staticmethod
    def _running(context):
        if context.cancelled.is_set():
            raise asyncio.CancelledError
