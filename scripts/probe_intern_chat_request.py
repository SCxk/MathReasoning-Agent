#!/usr/bin/env python3
"""Probe Intern chat request parameters that may trigger HTTP 400.

Usage:
  export INTERN_API_KEY=...
  python scripts/probe_intern_chat_request.py

Optional:
  INTERN_PROBE_MODEL=intern-s2-preview-397b
  INTERN_PROBE_API_BASE=https://chat.intern-ai.org.cn/api/v1/chat/completions
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests


API_BASE = os.environ.get(
    "INTERN_PROBE_API_BASE",
    os.environ.get(
        "INTERN_API_BASE",
        "https://chat.intern-ai.org.cn/api/v1/chat/completions",
    ),
)
MODEL = os.environ.get(
    "INTERN_PROBE_MODEL",
    os.environ.get("INTERN_MODEL", "intern-s2"),
)


SYSTEM_PROMPT = """你是一个严谨的数学推理智能体。
你需要解决用户给出的数学问题，并输出可判分的最终答案。
请优先按用户给定的 JSON 协议组织每次回复，便于程序解析和多轮推进。
复杂题必须先用 solve_step 逐步推进，最后用 final_answer 收敛。
"""


USER_PROMPT = """请解决下面的数学题。请按下面的 JSON 协议输出，便于程序解析。
你最多只能输出 32 次 solve_step；达到上限后必须输出 final_answer，不得继续 solve_step。
如果题目需要较长推理，不要一次写完整答案；先输出：
{"type":"solve_step","step_summary":"...","known_facts":["..."],"derived_results":["..."],"remaining_tasks":["..."],"is_ready_for_final":false}
若已经可以作答，输出：
{"type":"final_answer","answer":"...","reasoning_summary":"..."}

题目：
求 1+1。
"""


def make_payload(max_tokens: int, thinking_mode: bool | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    if thinking_mode is not None:
        payload["thinking_mode"] = thinking_mode
    return payload


def post(payload: dict[str, Any]) -> tuple[int | None, str]:
    raw_key = os.environ.get("INTERN_API_KEY")
    if not raw_key:
        raise RuntimeError("Missing INTERN_API_KEY")
    authorization = raw_key if raw_key.startswith("Bearer ") else f"Bearer {raw_key}"
    response = requests.post(
        API_BASE,
        headers={
            "Content-Type": "application/json",
            "Authorization": authorization,
        },
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=120,
    )
    text = response.text[:1000]
    return response.status_code, text


def main() -> int:
    cases = [
        ("max_tokens=0 thinking_mode=true", 0, True),
        ("max_tokens=0 thinking_mode=false", 0, False),
        ("max_tokens=4096 thinking_mode=true", 4096, True),
        ("max_tokens=4096 thinking_mode=false", 4096, False),
        ("max_tokens=4096 thinking_mode omitted", 4096, None),
    ]
    print(f"api_base={API_BASE}")
    print(f"model={MODEL}")
    for label, max_tokens, thinking_mode in cases:
        payload = make_payload(max_tokens=max_tokens, thinking_mode=thinking_mode)
        try:
            status, body = post(payload)
            print(f"\n[{label}] status={status}")
            print(body)
        except Exception as exc:  # noqa: BLE001 - diagnostic script.
            print(f"\n[{label}] exception={type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
