import json
import math
import re
from typing import Any

from agent_platform.models import PlatformError


_PRIVATE_KEYS = {
    "answer", "answers", "reference_answer", "reference_answers", "hidden_answer",
    "ground_truth", "api_key", "apikey", "authorization", "password", "secret",
    "token", "access_token", "credentials", "prompt", "system_prompt",
    "raw_response", "raw_model_response", "debug_trace",
}
_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|hf|ghp|github_pat)-?[A-Za-z0-9_\-]{16,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)\b(?:api[_ -]?key|password|secret|access[_ -]?token)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)\b(?:postgres(?:ql)?|redis|https?)://[^\s/@]+:[^\s/@]+@"),
)
_LOCAL_PATH = re.compile(r"[A-Za-z]:[\\/][^\s<>\"']+")


def private_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in _PRIVATE_KEYS or normalized.endswith(("_api_key", "_password", "_secret"))


def sanitize_text(value: str) -> str:
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[redacted]", value)
    return _LOCAL_PATH.sub("[local path]", value)


def sanitize(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "[depth limit]"
    if isinstance(value, str):
        return sanitize_text(value[:48000])
    if isinstance(value, dict):
        return {
            str(key): sanitize(item, depth + 1)
            for key, item in list(value.items())[:100]
            if not private_key(str(key))
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(item, depth + 1) for item in value[:100]]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return "[unsupported value]"


def validate_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    def inspect(value: Any, depth: int = 0) -> None:
        if depth > 8:
            raise PlatformError("metadata_too_deep", 400)
        if isinstance(value, dict):
            for key, item in value.items():
                if private_key(key):
                    raise PlatformError("reserved_metadata_field", 400)
                inspect(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                inspect(item, depth + 1)

    value = metadata or {}
    inspect(value)
    try:
        size = len(json.dumps(value, allow_nan=False).encode("utf-8"))
    except ValueError:
        raise PlatformError("invalid_metadata", 400) from None
    if size > 8000:
        raise PlatformError("metadata_too_large", 413)
    return sanitize(value)
