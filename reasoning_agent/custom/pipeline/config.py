from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineConfig:
    """业务编排层配置。

    这里放 pipeline 级别的开关和阈值；底层 ReAct 循环的模型调用、
    工具调用和 token 配置仍由 AgentConfig 管理。
    """

    max_candidates: int = 1
    enable_classify: bool = False
    enable_plan: bool = False
    enable_verify: bool = False
    enable_repair: bool = False
    enable_model_verifier: bool = False
    max_repair_attempts: int = 1
    min_answer_chars_for_proof: int = 80
