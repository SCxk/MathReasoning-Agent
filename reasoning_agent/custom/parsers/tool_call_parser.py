import json
from typing import Any

from reasoning_agent.custom.runner.events import (
    FinalAnswerEvent,
    InvalidEvent,
    ModelEvent,
    SolveStepEvent,
    ToolCallEvent,
)
from reasoning_agent.custom.parsers.json_parser import extract_json_object


def parse_model_event(raw: str | dict[str, Any]) -> ModelEvent:
    if isinstance(raw, dict):
        native_event = _parse_native_message(raw)
        if native_event is not None:
            return native_event
        content = raw.get("content", "")
        if isinstance(content, str):
            return _parse_content_event(content)
        return InvalidEvent(raw=str(raw), message="assistant message has no parsable content")

    return _parse_content_event(raw)


def _parse_native_message(message: dict[str, Any]) -> ModelEvent | None:
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list) or not tool_calls:
        return None

    tool_call = tool_calls[0]
    if not isinstance(tool_call, dict):
        return InvalidEvent(raw=str(message), message="tool_call must be an object")

    function = tool_call.get("function", {})
    if not isinstance(function, dict):
        return InvalidEvent(raw=str(message), message="tool_call.function must be an object")

    name = function.get("name", "")
    if not isinstance(name, str) or not name.strip():
        return InvalidEvent(raw=str(message), message="tool_call.function.name is empty")

    raw_arguments = function.get("arguments", {})
    if isinstance(raw_arguments, str):
        try:
            arguments = json.loads(raw_arguments) if raw_arguments.strip() else {}
        except json.JSONDecodeError:
            return InvalidEvent(
                raw=str(message),
                message="tool_call.function.arguments is not valid JSON",
            )
    else:
        arguments = raw_arguments

    if not isinstance(arguments, dict):
        return InvalidEvent(
            raw=str(message),
            message="tool_call.function.arguments must be a JSON object",
        )

    call_id = tool_call.get("id", "")
    assistant_message = dict(message)
    assistant_message["tool_calls"] = [tool_call]
    return ToolCallEvent(
        name=name.strip(),
        arguments=arguments,
        call_id=call_id if isinstance(call_id, str) else "",
        assistant_message=assistant_message,
    )


def _parse_content_event(raw: str) -> ModelEvent:
    data = extract_json_object(raw)
    if not data:
        return InvalidEvent(raw=raw, message="response does not contain a JSON object")

    event_type = data.get("type")
    if event_type == "final_answer":
        answer = data.get("answer", "")
        if not isinstance(answer, str) or not answer.strip():
            return InvalidEvent(raw=raw, message="final_answer.answer is empty")
        summary = data.get("reasoning_summary", "")
        return FinalAnswerEvent(
            answer=answer.strip(),
            reasoning_summary=summary if isinstance(summary, str) else "",
        )

    if event_type == "tool_call":
        tool = data.get("tool", "")
        arguments = data.get("arguments", {})
        if not isinstance(tool, str) or not tool.strip():
            return InvalidEvent(raw=raw, message="tool_call.tool is empty")
        if not isinstance(arguments, dict):
            return InvalidEvent(raw=raw, message="tool_call.arguments must be an object")
        return ToolCallEvent(name=tool.strip(), arguments=arguments)

    if event_type == "solve_step":
        return SolveStepEvent(
            step_summary=_as_text(data.get("step_summary", "")),
            known_facts=_as_text_list(data.get("known_facts", [])),
            derived_results=_as_text_list(data.get("derived_results", [])),
            remaining_tasks=_as_text_list(data.get("remaining_tasks", [])),
            is_ready_for_final=bool(data.get("is_ready_for_final", False)),
        )

    return InvalidEvent(raw=raw, message=f"unknown event type: {event_type}")


def _as_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else str(value or "").strip()


def _as_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _as_text(item))]
