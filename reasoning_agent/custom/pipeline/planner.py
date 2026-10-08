from reasoning_agent.custom.pipeline.context import PipelineContext
from reasoning_agent.custom.pipeline.types import Plan, ProblemProfile


class Planner:
    """根据题型生成业务层解题计划。

    计划用于约束后续节点的职责，不要求第一版做复杂推理。
    """

    def run(self, ctx: PipelineContext, profile: ProblemProfile) -> Plan:
        if profile.task_type == "choice":
            return Plan(
                strategy="compare_options",
                steps=["理解题干", "逐项判断选项", "给出明确选项"],
                risk_points=["选项格式不清晰", "只给推理不给选项"],
            )

        if profile.task_type == "fill_blank":
            return Plan(
                strategy="derive_final_expression",
                steps=["提取条件", "推导或计算目标量", "输出最终结果"],
                risk_points=["表达式化简错误", "最终结果格式不完整"],
            )

        if profile.task_type == "proof":
            return Plan(
                strategy="construct_proof",
                steps=["明确命题", "组织关键引理或推理链", "写出完整证明"],
                risk_points=["证明跳步", "只给结论没有论证"],
            )

        return Plan(
            strategy="solve_with_reasoning",
            steps=["分析题意", "推导关键关系", "给出可独立判分的答案"],
            risk_points=["计算错误", "答案缺少必要步骤"],
        )
