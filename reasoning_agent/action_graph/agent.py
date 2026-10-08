from __future__ import annotations

from typing import Any

from .config import ActionGraphConfig
from .runtime import ActionGraphRuntime


class ActionGraphAgent:
    def __init__(self, client: Any, config: ActionGraphConfig | object | None = None, *args: Any, **kwargs: Any) -> None:
        del args, kwargs
        self.client = client
        self.config = ActionGraphConfig.from_object(config)

    def solve(self, problem: str, metadata: dict | None) -> dict:
        return ActionGraphRuntime(self.client, self.config).run(problem, metadata)
