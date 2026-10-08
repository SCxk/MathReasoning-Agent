from __future__ import annotations

import inspect
import json
import re
from typing import Any

from reasoning_agent.custom.parsers.json_parser import extract_json_object

from .action_registry import ACTION_REGISTRY
from .models import ActionDecision


def invoke_client(
    client: Any,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    timeout: float,
    thinking: bool,
    temperature: float,
) -> str:
    # InternChatClient recognizes thinking_mode. Passing enable_thinking here
    # would leave its default thinking mode enabled.
    kwargs: dict[str, Any] = {
        "messages": messages,
        "max_tokens": max_tokens,
        "thinking_mode": thinking,
        "temperature": temperature,
        "request_timeout": timeout,
        "return_message": True,
    }
    try:
        signature = inspect.signature(client.chat)
        accepts_kwargs = any(item.kind == inspect.Parameter.VAR_KEYWORD for item in signature.parameters.values())
        if not accepts_kwargs:
            kwargs = {key: value for key, value in kwargs.items() if key in signature.parameters}
    except (TypeError, ValueError):
        pass
    raw = client.chat(**kwargs)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return str(raw.get("content", ""))
    return str(getattr(raw, "content", raw) or "")


def parse_json(text: str) -> dict[str, Any]:
    try:
        data = extract_json_object(text)
    except Exception:
        data = None
    if not isinstance(data, dict):
        raise ValueError("invalid_json")
    return data


def parse_decision(text: str, default_target: str) -> ActionDecision:
    data = parse_json(text)
    action = str(data.get("action", "")).strip()
    if action not in ACTION_REGISTRY:
        raise ValueError("unknown_action")
    goal = str(data.get("goal", "")).strip()
    success = str(data.get("success_condition", "")).strip()
    if not goal or not success:
        raise ValueError("missing_decision_field")
    facts = data.get("required_fact_ids", [])
    if not isinstance(facts, list):
        raise ValueError("invalid_fact_ids")
    return ActionDecision(action, str(data.get("target_id") or default_target), goal, tuple(str(item) for item in facts), success, data.get("branch_hint"))


def parse_action_result(text: str) -> tuple[str, list[str]]:
    match = re.search(r"<ACTION_RESULT>\s*(\{.*?\})\s*</ACTION_RESULT>", text, re.S)
    if not match:
        return "", []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return "", []
    answer = str(data.get("answer", "")).strip()
    covers = data.get("covers", [])
    return answer, [str(item) for item in covers] if isinstance(covers, list) else []


def parse_reflection(text: str) -> dict[str, Any]:
    data = parse_json(text)
    verdict = str(data.get("verdict", "")).strip()
    if verdict not in {"accept", "repair", "reject_route"}:
        raise ValueError("invalid_verdict")
    for name in ("accepted_claims", "covered_subquestion_ids", "invalidated_claim_ids"):
        if not isinstance(data.get(name, []), list):
            raise ValueError(f"invalid_{name}")
    return data


def parse_branches(text: str) -> list[dict[str, str]]:
    data = parse_json(text)
    branches = data.get("branches", data if isinstance(data, list) else [])
    if not isinstance(branches, list):
        raise ValueError("invalid_branches")
    result = []
    for branch in branches:
        if not isinstance(branch, dict) or not all(str(branch.get(key, "")).strip() for key in ("conditions", "goal")):
            raise ValueError("invalid_branch")
        result.append({"conditions": str(branch["conditions"]), "goal": str(branch["goal"])})
    return result
