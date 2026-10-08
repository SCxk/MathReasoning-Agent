import json
from typing import Any

from reasoning_agent.custom.prompts.tool_use import EXTREMAL_PROBLEM_GUIDANCE


STEP_VERIFIER_SYSTEM_PROMPT = """你是数学推理校验器。
你的任务不是重新解题，而是判断当前 solve_step 是否可以被写入已接受状态。
你必须保守：未经证明的极值猜测、known result、跳步结论、错误代数变形都不能通过。
只输出一个 JSON 对象，不要输出 Markdown、代码块或 JSON 外文本。
"""


def build_step_verifier_messages(
    problem: str,
    state_summary: dict[str, Any],
    candidate_step: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": STEP_VERIFIER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "请校验下面这个 solve_step 是否可以被接受进解题状态。\n\n"
                "检查标准：\n"
                "1. step_summary 必须和题目目标相关。\n"
                "2. known_facts 只能包含题目条件、已接受 state 或基础数学事实。\n"
                "3. derived_results 必须能由题目、known_facts 或已接受 state 严格推出。\n"
                "4. 出现未经证明的结论、known result、worst-case is、by pigeonhole 但无具体论证时，必须 reject。\n"
                "5. 检查代数变形、变量含义、量词方向是否错误。\n"
                "6. 极值题必须区分下界构造、上界证明、取等或逼近条件。\n\n"
                "等价变形审计要求：\n"
                "1. 凡是 step 声称“不等式/方程等价于...”或“除以某正量得到...”，必须逐项代入复算。\n"
                "2. 必须检查除法后的每一项分母是否正确、变量位置是否正确、绝对值内两项是否来自原式同一侧。\n"
                "3. 如果 step 中出现两个不同的等价式、ratio 形式或变量对应关系，且它们不能由同一个原式同时推出，必须 reject。\n"
                "4. 如果 step 只是照抄策略预处理中的等价式，但没有完成本步代数检查，必须 reject；策略 guidance 不是已证明事实。\n\n"
                "有效推进要求：\n"
                "1. solve_step 不能只重复题意、复述已有 state 或列出下一步计划。\n"
                "2. derived_results 必须包含至少一个本轮已经完成的数学变形、计算、分类、引理或可验证结论。\n"
                "3. 如果 derived_results 的主要内容是“需要枚举/需要证明/需要计算/下一步做什么”，而没有实际完成，必须 reject。\n"
                "4. 如果 remaining_solve_steps ≤ 2，必须要求本步产生实质计算或证明推进；继续泛泛规划必须 reject。\n\n"
                "最值/极值/最小常数类题还必须检查下面的阶段约束：\n"
                f"{EXTREMAL_PROBLEM_GUIDANCE}"
                "如果 step 在尚未完成规范化时直接猜最终常数，或在没有完整下界/上界证明时"
                "把候选答案写入 known_facts/derived_results，必须 reject。\n\n"
                "如果当前 state 的 error_memory 中记录了已拒绝的 rejected_step_summary、"
                "rejected_derived_results 或 avoid_repeating，待校验 step 只要重复这些错误且"
                "没有补足严格证明，必须 reject，并指出重复了哪条错误记忆。\n\n"
                "输出只能是以下三种 JSON 之一：\n"
                "{\"verdict\":\"accept\",\"reason\":\"...\"}\n"
                "{\"verdict\":\"revise\",\"reason\":\"...\",\"revised_step\":"
                "{\"step_summary\":\"...\",\"known_facts\":[\"...\"],"
                "\"derived_results\":[\"...\"],\"remaining_tasks\":[\"...\"],"
                "\"is_ready_for_final\":false}}\n"
                "{\"verdict\":\"reject\",\"reason\":\"...\",\"retry_instruction\":\"...\"}\n\n"
                "原始题目：\n"
                f"{problem}\n\n"
                "当前已接受 state：\n"
                f"{json.dumps(state_summary, ensure_ascii=False)}\n\n"
                "待校验 solve_step：\n"
                f"{json.dumps(candidate_step, ensure_ascii=False)}"
            ),
        },
    ]


def build_logic_retry_message(
    reason: str,
    retry_instruction: str,
    state_summary: dict[str, Any],
) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            "上一轮 solve_step 未通过逻辑校验，因此没有写入 state。\n"
            f"拒绝原因：{reason}\n"
            f"修正要求：{retry_instruction}\n"
            "请同时遵守当前 state.error_memory；不要重复其中记录的已拒绝路线、候选结论或跳步推理。\n"
            "请基于当前已接受 state 重新输出一个 solve_step JSON。\n"
            "不要重复上一轮错误；不要直接使用未经证明的结论。\n"
            "当前已接受 state：\n"
            + json.dumps(state_summary, ensure_ascii=False)
        ),
    }
