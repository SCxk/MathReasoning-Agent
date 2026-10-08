import json
from typing import Any


STRATEGY_PREPROCESS_SYSTEM_PROMPT = """你是数学竞赛解题策略设计器。
你的任务不是解出最终答案，而是在正式解题前给出稳健的解题路线、阶段约束和风险规避。
不要猜最终答案，不要输出完整解答。
不要写任何具体候选常数、候选答案、known result、well-known result 或“答案可能是...”。
策略中的等价变形只能作为“需要验证的操作”提出，不能把未逐项检查过的代数式当作事实。
禁止硬编码兜底：不得按题目关键词、元数据、常见答案或历史失败模式生成固定结论。
只输出一个 JSON 对象。
"""


def build_strategy_preprocess_messages(
    problem: str,
    metadata: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": STRATEGY_PREPROCESS_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "请根据题目和元数据，生成本题的竞赛解题策略设计。\n"
                "要求只输出一个 JSON 对象，字段如下：\n"
                "{"
                "\"problem_type\":\"...\","
                "\"core_transforms\":[\"...\"],"
                "\"phase_plan\":[\"...\"],"
                "\"lower_bound_requirements\":[\"...\"],"
                "\"upper_bound_requirements\":[\"...\"],"
                "\"risk_controls\":[\"...\"],"
                "\"do_not\":[\"...\"],"
                "\"first_step_instruction\":\"...\""
                "}\n\n"
                "通用约束：\n"
                "1. 不允许猜最终答案或最终常数。\n"
                "2. 如果是最值/极值/最小常数题，必须要求先规范化/等价变形，再分别证明下界和上界。\n"
                "3. 下界必须有具体构造，并说明需要验证所有相关选择/排列。\n"
                "4. 上界必须给出任意输入下的选择策略，并逐步验证。\n"
                "5. 风险控制要指出最容易发生的跳步、变量混淆、未证明极值猜测。\n"
                "6. first_step_instruction 只能要求第一步做规范化、排序、变量替换或等价变形。\n"
                "7. 不要在任何字段中写具体候选常数、候选答案、known result、golden ratio/特殊常数等未证明提示。\n"
                "8. 如果建议做等价变形，必须提醒正式解题时逐项代入检查分母和变量位置；不要直接断言未验证等价式。\n\n"
                "9. 禁止硬编码兜底：策略只能给通用解题流程，不能给针对题目关键词、metadata idx、常见答案的固定兜底。\n\n"
                "元数据：\n"
                f"{json.dumps(metadata, ensure_ascii=False)}\n\n"
                "题目：\n"
                f"{problem}"
            ),
        },
    ]


def build_strategy_guidance_message(strategy_guidance: dict[str, Any]) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            "正式解题前的策略约束如下。后续 solve_step 必须遵守这些约束；"
            "这些不是已证明结论，不能直接写入 derived_results。"
            "如果策略内容与实际代数推导冲突，必须以正式推导为准并忽略策略：\n"
            + json.dumps(strategy_guidance, ensure_ascii=False)
        ),
    }
