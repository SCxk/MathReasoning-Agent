import os
from typing import Any

from reasoning_agent.custom import CustomAgent
from reasoning_agent.custom2 import Custom2Agent


DEFAULT_AGENT_MODE = "custom2_staged"
SUPPORTED_AGENT_MODES = {"custom", "custom2", "custom2_staged", "custom2_action", "baseline"}
CLIENT_TIMEOUT_TARGET_SECONDS = 360.0


def raise_socket_timeout(client: Any, target: float = CLIENT_TIMEOUT_TARGET_SECONDS) -> Any:
    """Raise a writable client timeout when it is below the local target.

    Platform clients are injected and may not expose a writable ``timeout``
    attribute, so all access and assignment failures are intentionally ignored.
    The client object is always returned for convenient use by constructors.
    """
    try:
        current = getattr(client, "timeout")
        if current is None or float(current) >= float(target):
            return client
        setattr(client, "timeout", target)
    except (AttributeError, TypeError, ValueError, OverflowError):
        pass
    return client


def resolve_agent_mode(agent_mode: str | None = None) -> str:
    mode = agent_mode or os.environ.get("REASONING_AGENT_MODE", DEFAULT_AGENT_MODE)
    normalized = str(mode).strip().lower()
    if normalized == "default":
        normalized = DEFAULT_AGENT_MODE
    if normalized not in SUPPORTED_AGENT_MODES:
        allowed = ", ".join(sorted(SUPPORTED_AGENT_MODES))
        raise ValueError(f"Unknown agent mode: {mode}. Allowed modes: {allowed}.")
    return normalized


class ReasoningAgent:
    """Library facade for local experiments with alternate reasoning runtimes.

    The Web backend uses StagedAdapter directly rather than this mode dispatcher.
    """

    def __init__(
        self,
        client: Any,
        config: Any | None = None,
        *args: Any,
        agent_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        client = raise_socket_timeout(client)
        mode = resolve_agent_mode(agent_mode or kwargs.pop("agent_mode", None))
        self.agent_mode = mode
        self._agent = self._build_agent(mode, client, config, *args, **kwargs)

    def solve(self, problem: str, metadata: dict | None) -> dict:
        return self._agent.solve(problem, metadata)

    def _build_agent(
        self,
        mode: str,
        client: Any,
        config: Any | None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if mode == "custom":
            return CustomAgent(client, config, *args, **kwargs)

        if mode == "custom2":
            return Custom2Agent(client, config, *args, **kwargs)

        if mode == "custom2_staged":
            staged_config = config
            if staged_config is None:
                from reasoning_agent.custom.config import AgentConfig

                staged_config = AgentConfig(custom2_solver_protocol="staged")
            elif getattr(staged_config, "custom2_solver_protocol", "") != "staged":
                raise ValueError("custom2_staged requires custom2_solver_protocol='staged'")
            return Custom2Agent(client, staged_config, *args, **kwargs)

        if mode == "custom2_action":
            from reasoning_agent.action_graph import ActionGraphAgent

            return ActionGraphAgent(client, config, *args, **kwargs)

        if mode == "baseline":
            try:
                from reasoning_agent.baseline import BaselineAgent
            except ImportError as exc:
                raise RuntimeError(
                    "BaselineAgent requires the optional lagent package. Install it or use "
                    "REASONING_AGENT_MODE=custom."
                ) from exc
            return BaselineAgent(client, config, *args, **kwargs)

        raise AssertionError(f"unhandled agent mode: {mode}")
