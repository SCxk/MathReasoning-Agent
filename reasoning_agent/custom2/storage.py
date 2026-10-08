import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from reasoning_agent.custom.parsers.json_parser import make_json_safe
from reasoning_agent.custom2.models import AgentState


class RuntimeLogger:
    """Append-only local logger for real-time custom2 runtime inspection."""

    def __init__(self, run_dir: Path | None) -> None:
        self.run_dir = run_dir
        self.sequence = 0
        if self.run_dir is not None:
            self.run_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, metadata: dict | None = None) -> "RuntimeLogger":
        root = os.environ.get("REASONING_AGENT_CUSTOM2_LOG_DIR", "").strip()
        if not root:
            return cls(run_dir=None)
        idx = ""
        if isinstance(metadata, dict) and metadata.get("idx") is not None:
            idx = f"idx-{metadata['idx']}-"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = Path(root).expanduser() / f"{idx}{timestamp}-{uuid4().hex[:8]}"
        return cls(run_dir=run_dir)

    @property
    def enabled(self) -> bool:
        return self.run_dir is not None

    def write_config(self, problem: str, metadata: dict | None, config: Any) -> None:
        if self.run_dir is None:
            return
        payload = {
            "problem_chars": len(problem),
            "metadata": make_json_safe(metadata or {}),
            "config": make_json_safe(_config_to_dict(config)),
        }
        self._write_json(self.run_dir / "config.json", payload)

    def emit(self, event_type: str, data: dict, state: AgentState) -> None:
        if self.run_dir is None:
            return
        self.sequence += 1
        now = datetime.now(timezone.utc).isoformat()
        event = {
            "seq": self.sequence,
            "time": now,
            "type": event_type,
            "data": make_json_safe(data),
        }
        state_payload = {
            "seq": self.sequence,
            "time": now,
            "state": make_json_safe(state.model_dump()),
        }
        self._append_jsonl(self.run_dir / "events.jsonl", event)
        self._append_jsonl(self.run_dir / "states.jsonl", state_payload)

    def write_final(self, final_response: str, trace: list[dict], state: AgentState) -> None:
        if self.run_dir is None:
            return
        self._write_json(
            self.run_dir / "final.json",
            {
                "final_response": final_response,
                "trace": make_json_safe(trace),
                "state": make_json_safe(state.model_dump()),
            },
        )

    @staticmethod
    def _append_jsonl(path: Path, payload: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            handle.flush()

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()


def _config_to_dict(config: Any) -> dict:
    if config is None:
        return {}
    if hasattr(config, "__dict__"):
        return dict(config.__dict__)
    return {"value": str(config)}
