import json
import os
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

import requests


DEFAULT_API_BASE = "https://chat.intern-ai.org.cn/api/v1/chat/completions"
DEFAULT_MODEL = "intern-s2-preview"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 8192
DEFAULT_THINKING_MODE = True
DEBUG_CHAT_REQUESTS = os.environ.get("INTERN_CHAT_DEBUG", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}
DUMP_CHAT_REQUESTS = os.environ.get("INTERN_CHAT_DUMP_REQUEST", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}
DUMP_CHAT_REQUEST_DIR = os.environ.get("INTERN_CHAT_REQUEST_DUMP_DIR", "").strip()

ChatMessage = Dict[str, Any]
ChatResponse = Union[str, ChatMessage]


class ChatCompletionError(RuntimeError):
    """Retain bounded server diagnostics without including request contents."""

    def __init__(
        self,
        attempts: int,
        error: Exception | None,
        *,
        status_code: int | None = None,
        response_body: str = "",
    ) -> None:
        self.attempts = attempts
        self.status_code = status_code
        self.response_body = " ".join(str(response_body or "").split())[:1000]
        super().__init__(f"Chat completion failed after {attempts} attempts: {error}")


class InternChatClient:
    """OpenAI-compatible chat client configured by the backend environment."""

    def __init__(
        self,
        timeout: int = 240,
        retry: int = 3,
        default_args: Optional[Mapping[str, Any]] = None,
        **request_args: Any,
    ) -> None:
        raw_api_key = os.environ.get("INTERN_API_KEY")
        if not raw_api_key:
            raise RuntimeError("Missing API key. Set INTERN_API_KEY.")
        self.authorization = (
            raw_api_key if raw_api_key.startswith("Bearer ") else f"Bearer {raw_api_key}"
        )
        self.api_base = os.environ.get("INTERN_API_BASE", DEFAULT_API_BASE)
        self.model = os.environ.get("INTERN_MODEL", DEFAULT_MODEL)
        self.timeout = timeout
        self.retry = retry
        self.default_args = dict(default_args or {})
        self.default_args.update(request_args)

    def chat(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        *,
        thinking_mode: Optional[bool] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        return_message: bool = False,
        request_timeout: Optional[float] = None,
        **request_args: Any,
    ) -> ChatResponse:
        """Create a chat completion.

        Extra request arguments are passed through to the HTTP API. Arguments
        supplied to ``chat`` override client-wide ``default_args``.

        Text completions are returned as strings for backwards compatibility.
        When the model requests a tool call, the complete assistant message is
        returned so that callers can read ``tool_calls`` and append the message
        to the next request.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "thinking_mode": DEFAULT_THINKING_MODE,
        }
        payload.update(self.default_args)
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if thinking_mode is not None:
            payload["thinking_mode"] = thinking_mode
        if tools is not None:
            payload["tools"] = tools
        payload.update(request_args)
        # ``messages`` is the only required per-call argument and must not be
        # replaced accidentally by client-wide defaults.
        payload["messages"] = messages

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.authorization,
        }

        # A staged long-form solver deliberately gets one uninterrupted HTTP
        # attempt.  Retrying a request that has already consumed the entire
        # 10-minute reasoning window only recreates the same expensive prompt
        # and leaves no time for the compact recovery.  Short control calls
        # keep the normal client retry policy.  ``request_timeout`` is set by
        # the agent's phase budget, so this remains a local-client behavior
        # and does not alter the platform-injected client contract.
        single_long_attempt = bool(
            request_timeout is not None
            and float(request_timeout) > float(self.timeout)
        )
        retry_count = 1 if single_long_attempt else self.retry
        last_error = None
        last_status_code: int | None = None
        last_response_body = ""
        call_started_monotonic = time.perf_counter()
        for attempt in range(retry_count):
            started_at = datetime.now(timezone.utc)
            started_monotonic = time.perf_counter()
            try:
                transport_timeout = (
                    float(request_timeout)
                    if single_long_attempt and request_timeout is not None
                    else float(self.timeout)
                )
                if request_timeout is not None:
                    request_remaining = float(request_timeout) - (
                        time.perf_counter() - call_started_monotonic
                    )
                    if request_remaining <= 0:
                        break
                    transport_timeout = min(transport_timeout, request_remaining)
                response = requests.post(
                    self.api_base,
                    headers=headers,
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    timeout=transport_timeout,
                )
                response.raise_for_status()
                data = response.json()
                message = data["choices"][0]["message"]
                ended_at = datetime.now(timezone.utc)
                duration_seconds = max(0.0, time.perf_counter() - started_monotonic)
                if DUMP_CHAT_REQUESTS:
                    self._dump_request_payload_safely(
                        payload,
                        attempt=attempt + 1,
                        status_code=getattr(response, "status_code", None),
                        response_body=getattr(response, "text", "") or "",
                        started_at=started_at.isoformat(),
                        ended_at=ended_at.isoformat(),
                        duration_seconds=duration_seconds,
                    )
                if return_message:
                    enriched_message = dict(message)
                    finish_reason = data["choices"][0].get("finish_reason")
                    usage = data.get("usage")
                    if finish_reason is not None:
                        enriched_message["_finish_reason"] = finish_reason
                    if usage is not None:
                        enriched_message["_usage"] = usage
                    return enriched_message
                if "tool_calls" in message:
                    return message
                return message["content"]
            except Exception as exc:  # noqa: BLE001 - keep sample robust and simple.
                last_error = exc
                ended_at = datetime.now(timezone.utc)
                duration_seconds = max(0.0, time.perf_counter() - started_monotonic)
                response = getattr(exc, "response", None)
                status_code = getattr(response, "status_code", None)
                last_status_code = status_code if isinstance(status_code, int) else None
                last_response_body = getattr(response, "text", "") if response else ""
                if DEBUG_CHAT_REQUESTS:
                    self._log_request_summary(
                        payload,
                        attempt=attempt + 1,
                        retry=retry_count,
                        status_code=status_code,
                        error=exc,
                        response_body=getattr(response, "text", "") if response else "",
                        started_at=started_at.isoformat(),
                        ended_at=ended_at.isoformat(),
                        duration_seconds=duration_seconds,
                    )
                if DUMP_CHAT_REQUESTS:
                    self._dump_request_payload_safely(
                        payload,
                        attempt=attempt + 1,
                        error=exc,
                        status_code=status_code,
                        response_body=getattr(response, "text", "") if response else "",
                        started_at=started_at.isoformat(),
                        ended_at=ended_at.isoformat(),
                        duration_seconds=duration_seconds,
                    )
                if attempt + 1 < retry_count:
                    retry_delay = float(2**attempt)
                    if request_timeout is not None:
                        request_remaining = float(request_timeout) - (
                            time.perf_counter() - call_started_monotonic
                        )
                        if request_remaining <= retry_delay:
                            break
                    time.sleep(retry_delay)

        raise ChatCompletionError(
            retry_count,
            last_error,
            status_code=last_status_code,
            response_body=last_response_body,
        )

    @staticmethod
    def _log_request_summary(
        payload: dict[str, Any],
        *,
        attempt: int,
        retry: int,
        status_code: int | None = None,
        error: Exception | None = None,
        response_body: str = "",
        started_at: str | None = None,
        ended_at: str | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        messages = payload.get("messages", [])
        message_summaries: list[dict[str, Any]] = []
        total_chars = 0
        if isinstance(messages, list):
            for index, message in enumerate(messages):
                if not isinstance(message, dict):
                    message_summaries.append({"index": index, "type": type(message).__name__})
                    continue
                content = message.get("content")
                if isinstance(content, str):
                    content_text = content
                    content_type = "str"
                else:
                    try:
                        content_text = json.dumps(content, ensure_ascii=False)
                    except TypeError:
                        content_text = str(content)
                    content_type = type(content).__name__
                total_chars += len(content_text)
                message_summaries.append(
                    {
                        "index": index,
                        "role": message.get("role"),
                        "content_type": content_type,
                        "chars": len(content_text),
                        "preview": content_text[:300],
                    }
                )

        summary = {
            "attempt": attempt,
            "retry": retry,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": duration_seconds,
            "model": payload.get("model"),
            "temperature": payload.get("temperature"),
            "max_tokens": payload.get("max_tokens"),
            "thinking_mode": payload.get("thinking_mode"),
            "status_code": status_code,
            "error": str(error) if error else "",
            "tool_count": len(payload.get("tools", []) or []),
            "message_count": len(messages) if isinstance(messages, list) else None,
            "message_chars": total_chars,
            "messages": message_summaries,
        }
        if response_body:
            summary["response_body"] = response_body[:1000]
        print(
            "[intern_chat_request] " + json.dumps(summary, ensure_ascii=False),
            file=sys.stderr,
        )

    @staticmethod
    def _dump_request_payload(
        payload: dict[str, Any],
        *,
        attempt: int,
        error: Exception | None = None,
        status_code: int | None = None,
        response_body: str = "",
        started_at: str | None = None,
        ended_at: str | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        if not DUMP_CHAT_REQUEST_DIR:
            return
        dump_dir = Path(DUMP_CHAT_REQUEST_DIR).expanduser()
        dump_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        status_label = str(status_code) if status_code is not None else "error"
        path = dump_dir / f"{timestamp}-{status_label}-attempt-{attempt}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "status_code": status_code,
                    "success": error is None,
                    "error": str(error) if error else "",
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "duration_seconds": duration_seconds,
                    "response_body": (response_body or "")[:8000],
                    "payload": payload,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")

    @classmethod
    def _dump_request_payload_safely(
        cls,
        payload: dict[str, Any],
        *,
        attempt: int,
        error: Exception | None = None,
        status_code: Any = None,
        response_body: str = "",
        started_at: str | None = None,
        ended_at: str | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        normalized_status = status_code if isinstance(status_code, int) else None
        if normalized_status is None and error is None:
            normalized_status = 200
        normalized_body = response_body if isinstance(response_body, str) else ""
        try:
            cls._dump_request_payload(
                payload,
                attempt=attempt,
                error=error,
                status_code=normalized_status,
                response_body=normalized_body,
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=duration_seconds,
            )
        except Exception as dump_error:  # noqa: BLE001 - diagnostics must not break chat.
            if DEBUG_CHAT_REQUESTS:
                print(
                    "[intern_chat_dump_error] " + json.dumps(
                        {"attempt": attempt, "error": str(dump_error)},
                        ensure_ascii=False,
                    ),
                    file=sys.stderr,
                )
