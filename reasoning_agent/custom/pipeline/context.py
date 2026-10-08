from dataclasses import dataclass, field
from typing import Any

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom.pipeline.config import PipelineConfig


@dataclass
class PipelineContext:
    problem: str
    metadata: dict[str, Any]
    agent_config: AgentConfig
    pipeline_config: PipelineConfig
    trace: list[dict[str, Any]] = field(default_factory=list)
    debug_trace: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    strategy_guidance: dict[str, Any] = field(default_factory=dict)
    strategy_preprocess_calls: int = 0
    repair_attempts: int = 0

    @classmethod
    def create(
        cls,
        problem: str,
        metadata: dict | None,
        agent_config: AgentConfig,
        pipeline_config: PipelineConfig,
    ) -> "PipelineContext":
        normalized_metadata = metadata if isinstance(metadata, dict) else {}
        return cls(
            problem=str(problem or "").strip(),
            metadata=dict(normalized_metadata),
            agent_config=agent_config,
            pipeline_config=pipeline_config,
        )

    def add_trace(self, step: str, content: dict[str, Any]) -> None:
        # trace 是业务层轨迹，会进入评测输入；这里只记录 pipeline 阶段摘要。
        self.trace.append({"step": step, "content": content})

    def add_debug_trace(self, event_type: str, content: dict[str, Any]) -> None:
        # debug_trace 保存模型调用、工具调用等细粒度调试信息；仍然不能写入
        # 完整提示词、原始模型回复、密钥、隐藏答案或本地路径。
        self.debug_trace.append({"type": event_type, "content": content})

    def add_error(self, exc: Exception) -> None:
        error = {"type": type(exc).__name__, "message": str(exc)}
        self.errors.append(error)
        self.add_trace("error", error)
