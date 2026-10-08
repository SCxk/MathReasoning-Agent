from typing import Any

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom.errors import InvalidToolRequest
from reasoning_agent.custom.tools.registry import ToolSpec


class ToolExecutor:
    def __init__(self, tools: dict[str, ToolSpec], config: AgentConfig) -> None:
        self.tools = tools
        self.config = config

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            spec = self._validate(name, arguments)
            result = spec.function(**arguments)
            return {"tool": name, "ok": True, "result": self._json_safe_result(result)}
        except Exception as exc:  # noqa: BLE001 - tool failures are model observations.
            return {
                "tool": name,
                "ok": False,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }

    def chat_tools(self) -> list[dict[str, Any]]:
        return [spec.to_chat_tool() for spec in self.tools.values()]

    def _validate(self, name: str, arguments: dict[str, Any]) -> ToolSpec:
        if name not in self.tools:
            raise InvalidToolRequest(f"unknown tool: {name}")
        if not isinstance(arguments, dict):
            raise InvalidToolRequest("tool arguments must be a JSON object")

        spec = self.tools[name]
        missing = [key for key in spec.required_arguments if key not in arguments]
        if missing:
            raise InvalidToolRequest(f"missing required arguments: {missing}")

        extra = [key for key in arguments if key not in spec.allowed_arguments]
        if extra:
            raise InvalidToolRequest(f"unexpected arguments: {extra}")
        return spec

    @staticmethod
    def _json_safe_result(result: Any) -> Any:
        if isinstance(result, (str, int, float, bool)) or result is None:
            return result
        if isinstance(result, list):
            return [ToolExecutor._json_safe_result(item) for item in result]
        if isinstance(result, dict):
            return {str(key): ToolExecutor._json_safe_result(value) for key, value in result.items()}
        return str(result)
