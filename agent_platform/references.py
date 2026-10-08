"""Public retrieved-source snapshots, never inferred mathematical correctness."""

import re
from typing import Any

from pydantic import ValidationError

from agent_platform.models import Task
from agent_platform.safety import sanitize
from agent_platform.tools.schemas import DocumentValue, Passage


def public_references(task: Task) -> list[dict[str, Any]]:
    found: dict[str, Passage] = {}
    for entry in list(task.tool_calls.values())[:64]:
        result = entry.get("result") or {}
        if entry.get("tool_name") != "document_search" or result.get("status") not in {"succeeded", "fallback"}:
            continue
        try:
            passages = DocumentValue.model_validate(result.get("value")).passages
        except ValidationError:
            continue
        for passage in passages:
            found.setdefault(passage.chunk_id, passage)
    selected = task.metadata.get("document_ids")
    response = task.final_response or ""
    output: list[dict[str, Any]] = []
    for passage in found.values():
        if selected is not None and passage.document_id not in selected:
            continue
        mentioned = bool(re.search(r"(?<![\w-])" + re.escape(passage.chunk_id) + r"(?![\w-])", response, re.I))
        output.append({
            "chunk_id": passage.chunk_id, "document_id": passage.document_id,
            "title": passage.source_metadata.title, "heading": passage.source_metadata.heading,
            "page_start": passage.page_start, "page_end": passage.page_end,
            "excerpt": passage.text, "citation_status": "mentioned_in_answer" if mentioned else "retrieved",
        })
        if len(output) == 20:
            break
    return sanitize(output)
