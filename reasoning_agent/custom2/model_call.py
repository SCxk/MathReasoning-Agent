from __future__ import annotations

from dataclasses import dataclass
import inspect
import json
import os
import queue
import sys
import threading
import time
from typing import Any

from reasoning_agent.custom.parsers.json_parser import make_json_safe
from reasoning_agent.custom2.models import AgentState
from reasoning_agent.custom2.state_manager import remaining_seconds


class ModelCallBudgetExhausted(TimeoutError):
    """Raised before a model call when its usable wall-clock budget is empty."""


class ModelCallTimedOut(TimeoutError):
    """Raised when a model call exceeds its runtime wall-clock deadline."""


@dataclass(frozen=True)
class ModelResponse:
    content: str
    reasoning_content: str = ""
    finish_reason: str | None = None
    token_usage: Any = None
    duration_seconds: float = 0.0


def call_model(
    client: Any,
    state: AgentState,
    debug_trace: list[dict] | None,
    call_type: str,
    *,
    allow_finalize_reserve: bool = False,
    max_timeout_seconds: float | None = None,
    **kwargs: Any,
) -> ModelResponse:
    """Call the injected client with a runtime-enforced wall-clock deadline."""

    timeout_seconds: float | None = None
    if state.efficient_runtime and state.deadline_at > 0:
        reserve = 0.0 if allow_finalize_reserve else state.finalize_reserve_seconds
        timeout_seconds = remaining_seconds(state) - reserve
        best_candidate_deadline = getattr(state, "best_candidate_deadline_at", 0.0)
        if best_candidate_deadline > 0:
            timeout_seconds = min(timeout_seconds, best_candidate_deadline - time.monotonic())
        if timeout_seconds <= 0:
            raise ModelCallBudgetExhausted(
                f"no time remains for {call_type} before the best-candidate return window"
            )
        if max_timeout_seconds is not None:
            timeout_seconds = min(timeout_seconds, max(0.001, float(max_timeout_seconds)))

    request_kwargs = dict(kwargs)
    request_kwargs["return_message"] = True
    if timeout_seconds is not None:
        request_kwargs["request_timeout"] = max(0.001, timeout_seconds)

    started_at = time.monotonic()
    try:
        raw = _invoke_with_timeout(
            client,
            request_kwargs,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        duration = max(0.0, time.monotonic() - started_at)
        _emit_live_model_debug(
            call_type,
            timeout_seconds,
            duration_seconds=duration,
            error=exc,
        )
        if debug_trace is not None:
            debug_trace.append(
                {
                    "type": "model_call_error",
                    "call_type": call_type,
                    "duration_seconds": duration,
                    "timeout_seconds": timeout_seconds,
                    "error_type": type(exc).__name__,
                    "content": str(exc)[:1000],
                }
            )
        raise

    duration = max(0.0, time.monotonic() - started_at)
    response = _normalize_response(raw, duration)
    _emit_live_model_debug(
        call_type,
        timeout_seconds,
        duration_seconds=duration,
        response=response,
    )
    if debug_trace is not None:
        debug_trace.append(_response_trace(call_type, response, timeout_seconds))
    return response


def _emit_live_model_debug(
    call_type: str,
    timeout_seconds: float | None,
    *,
    duration_seconds: float,
    response: ModelResponse | None = None,
    error: Exception | None = None,
) -> None:
    """Print a local-only response as soon as the request finishes."""
    if os.environ.get("CUSTOM2_DEBUG_MODEL_RESPONSES", "").strip().lower() not in {
        "1", "true", "yes", "y", "on",
    }:
        return
    event: dict[str, Any] = {
        "call_type": call_type,
        "duration_seconds": round(duration_seconds, 3),
        "timeout_seconds": timeout_seconds,
    }
    if response is not None:
        event.update({
            "status": "response",
            "content": response.content,
            "reasoning_content": response.reasoning_content,
            "finish_reason": response.finish_reason,
        })
    else:
        event.update({
            "status": "error",
            "error_type": type(error).__name__ if error else "UnknownError",
            "error": str(error or "")[:2000],
        })
    print("[custom2_model_response] " + json.dumps(event, ensure_ascii=False), file=sys.stderr, flush=True)


def _invoke_with_timeout(
    client: Any,
    request_kwargs: dict[str, Any],
    *,
    timeout_seconds: float | None,
) -> Any:
    if timeout_seconds is None:
        return _invoke_client(client, request_kwargs)

    result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def target() -> None:
        try:
            result_queue.put((True, _invoke_client(client, request_kwargs)))
        except BaseException as exc:  # propagate the client failure to the caller
            result_queue.put((False, exc))

    worker = threading.Thread(target=target, daemon=True, name="custom2-model-call")
    worker.start()
    # ``request_timeout`` is also passed to clients that support it.  Joining
    # at that exact same instant races the client's own timeout cleanup: the
    # wrapper can report ModelCallTimedOut while the HTTP/retry thread is
    # still alive, after which a recovery call creates a second in-flight
    # request for the same solve.  Under local concurrency this compounds
    # into a queue of abandoned calls.  Keep the requested budget unchanged,
    # but allow a tiny bounded grace period for the injected client to return
    # its timeout/error before declaring the call orphaned.
    cleanup_grace = min(2.0, max(0.005, timeout_seconds * 0.01))
    worker.join(timeout_seconds + cleanup_grace)
    if worker.is_alive():
        raise ModelCallTimedOut(
            f"model call exceeded wall-clock timeout of {timeout_seconds:.3f}s"
        )
    succeeded, value = result_queue.get_nowait()
    if succeeded:
        return value
    raise value


def _invoke_client(client: Any, request_kwargs: dict[str, Any]) -> Any:
    chat = client.chat
    try:
        signature = inspect.signature(chat)
    except (TypeError, ValueError):
        signature = None
    if signature is not None:
        if "request_timeout" not in signature.parameters:
            request_kwargs.pop("request_timeout", None)
        accepts_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
        if not accepts_kwargs:
            request_kwargs = {
                key: value
                for key, value in request_kwargs.items()
                if key in signature.parameters
            }
    return chat(**request_kwargs)


def _normalize_response(raw: Any, duration: float) -> ModelResponse:
    if isinstance(raw, str):
        return ModelResponse(content=raw, duration_seconds=duration)
    if isinstance(raw, dict):
        content = raw.get("content", "")
        reasoning_content = raw.get("reasoning_content", "")
        return ModelResponse(
            content=content if isinstance(content, str) else str(content or ""),
            reasoning_content=(
                reasoning_content
                if isinstance(reasoning_content, str)
                else str(reasoning_content or "")
            ),
            finish_reason=_optional_text(
                raw.get("_finish_reason", raw.get("finish_reason"))
            ),
            token_usage=raw.get("_usage", raw.get("usage")),
            duration_seconds=duration,
        )
    content = getattr(raw, "content", "")
    reasoning_content = getattr(raw, "reasoning_content", "")
    return ModelResponse(
        content=content if isinstance(content, str) else str(content or ""),
        reasoning_content=(
            reasoning_content
            if isinstance(reasoning_content, str)
            else str(reasoning_content or "")
        ),
        finish_reason=_optional_text(getattr(raw, "finish_reason", None)),
        token_usage=getattr(raw, "usage", None),
        duration_seconds=duration,
    )


def _response_trace(
    call_type: str,
    response: ModelResponse,
    timeout_seconds: float | None,
) -> dict:
    content = response.content
    excerpt_chars = 300
    return {
        "type": "model_response",
        "call_type": call_type,
        "content_head": content[:excerpt_chars],
        "content_tail": content[-excerpt_chars:] if len(content) > excerpt_chars else content,
        "content_length": len(content),
        "reasoning_content_length": len(response.reasoning_content),
        "duration_seconds": response.duration_seconds,
        "timeout_seconds": timeout_seconds,
        "token_usage": make_json_safe(response.token_usage),
        "finish_reason": response.finish_reason,
    }


def _optional_text(value: Any) -> str | None:
    return None if value is None else str(value)
