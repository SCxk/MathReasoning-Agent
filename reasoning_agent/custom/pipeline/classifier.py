from reasoning_agent.custom.pipeline.context import PipelineContext
from reasoning_agent.custom.pipeline.types import ProblemProfile


class ProblemClassifier:
    """轻量题型识别节点。

    第一版优先使用稳定规则，避免为分类额外消耗模型调用。后续可以在这里接入
    模型分类器，但输出仍保持 ProblemProfile。
    """

    def run(self, ctx: PipelineContext) -> ProblemProfile:
        text = ctx.problem
        lowered = text.lower()

        if any(marker in text for marker in ("证明", "证：", "求证")):
            task_type = "proof"
            answer_style = "proof"
        elif any(marker in text for marker in ("选择", "选项", "A.", "B.", "C.", "D.")):
            task_type = "choice"
            answer_style = "option"
        elif any(marker in text for marker in ("填空", "____", "空格")):
            task_type = "fill_blank"
            answer_style = "expression"
        elif any(marker in lowered for marker in ("prove", "show that", "证明")):
            task_type = "proof"
            answer_style = "proof"
        else:
            task_type = "derivation"
            answer_style = "explanation"

        needs_tools = any(
            marker in lowered
            for marker in ("calculate", "compute", "numerical", "求值", "计算")
        )

        difficulty = "unknown"
        if len(text) < 120:
            difficulty = "easy"
        elif len(text) < 600:
            difficulty = "medium"
        else:
            difficulty = "hard"

        return ProblemProfile(
            task_type=task_type,
            difficulty=difficulty,
            needs_tools=needs_tools,
            answer_style=answer_style,
        )
