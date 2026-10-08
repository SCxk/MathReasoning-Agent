"""Bounded, scoped keyset pagination for public chat history."""

import base64
from datetime import datetime, timezone
import json
import re

from agent_platform.models import PlatformError
from agent_platform.safety import sanitize_text


def member(created_at: datetime, identifier: str) -> str:
    return created_at.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ":" + identifier


def cursor_member(cursor: str | None, scope: str) -> str | None:
    if cursor is None:
        return None
    try:
        if not cursor or len(cursor) > 512:
            raise ValueError
        data = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        value = data["member"]
        if data["scope"] != scope or not re.fullmatch(r"[0-9]{20}:[0-9a-f-]{36}", value):
            raise ValueError
        datetime.strptime(value[:20], "%Y%m%d%H%M%S%f")
        return value
    except (ValueError, KeyError, TypeError):
        raise PlatformError("invalid_cursor", 400) from None


def next_cursor(value: str, scope: str) -> str:
    return base64.urlsafe_b64encode(json.dumps({"scope": scope, "member": value}).encode()).decode()


def cursor_parts(cursor: str | None, scope: str):
    value = cursor_member(cursor, scope)
    if value is None:
        return None
    return datetime.strptime(value[:20], "%Y%m%d%H%M%S%f").replace(tzinfo=timezone.utc), value[21:]


def page_cursor(values: list[str], limit: int, scope: str) -> str | None:
    return next_cursor(values[limit - 1], scope) if len(values) > limit else None


def session_summary(session, tasks):
    first = min(tasks, key=lambda task: (task.accepted_at, task.id)) if tasks else None
    latest = max((task.accepted_at for task in tasks), default=session.created_at)
    return {
        "id": session.id, "title": sanitize_text(first.problem[:60]) if first else "",
        "created_at": session.created_at.isoformat(), "last_activity_at": latest.isoformat(),
        "task_count": len(tasks),
    }
