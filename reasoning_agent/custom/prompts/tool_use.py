import json
from typing import Any

from reasoning_agent.custom.prompts.system import SYSTEM_PROMPT
from reasoning_agent.prompt_utils import build_invalid_json_retry_message


EXTREMAL_PROBLEM_GUIDANCE = (
    "最值/极值/最小常数类题目的解题阶段约束：\n"
    "1. 不允许先猜最终常数或最终答案；猜测只能放在 remaining_tasks，不能放入 known_facts 或 derived_results。\n"
    "2. 第一阶段只做规范化、排序、变量替换、等价变形，得到清晰的等价问题。\n"
    "3. 第二阶段找下界：必须给出具体构造，并验证该构造下所有相关选择/排列都不能突破下界。\n"
    "4. 第三阶段找上界：必须对任意输入给出明确选择策略，并逐步验证不等式成立。\n"
    "5. 只有下界和上界已经相等，且都在已接受 state 中出现，才允许输出 final_answer。\n"
    "6. 禁止硬编码兜底：不得根据题目关键词、元数据 idx、常见答案或失败重试历史直接套用固定常数/固定结论。\n"
)


def build_initial_messages(problem: str, max_solve_steps: int = 14) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "请解决下面的数学题。请按下面的 JSON 协议输出，便于程序解析。\n"
                f"你最多只能输出 {max_solve_steps} 次 solve_step；"
                "达到上限后必须输出 final_answer，不得继续 solve_step。\n"
                "如果题目需要较长推理，不要一次写完整答案；先输出："
                "{\"type\":\"solve_step\",\"step_summary\":\"...\","
                "\"known_facts\":[\"...\"],\"derived_results\":[\"...\"],"
                "\"remaining_tasks\":[\"...\"],\"is_ready_for_final\":false}\n"
                "若已经可以作答，输出："
                "{\"type\":\"final_answer\",\"answer\":\"...\",\"reasoning_summary\":\"...\"}\n"
                "final_answer.answer 必须包含最终结论，且最终结果必须写在 \\boxed{} 中；"
                "\\boxed{} 内只能放答案值或最简数学表达式，不能放‘Thus the answer is’、"
                "‘答案为’或整句描述；一般函数公式优先写成 f(x)=...。"
                "证明题没有独立答案值时不要把自然语言结论硬塞进 box。\n"
                "若需要调用工具，输出："
                "{\"type\":\"tool_call\",\"tool\":\"工具名\",\"arguments\":{}}\n"
                "当前脚手架暂未开放数学工具；"
                "即使已经猜到候选答案，也不得因此直接输出 final_answer 。只有在完整证明已经形成并通过自检后才能输出 final_answer"
                "\n\n"
                f"{EXTREMAL_PROBLEM_GUIDANCE}"
                "\n\n"
                f"题目：\n{problem}"
            ),
        },
    ]


def build_observation_message(observation: dict[str, Any]) -> dict[str, str]:
    return {
        "role": "user",
        "content": "工具返回结果：\n" + json.dumps(observation, ensure_ascii=False),
    }


def build_solve_state_message(state_summary: dict[str, Any]) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            "已记录当前解题状态：\n"
            + json.dumps(state_summary, ensure_ascii=False)
            + "\n请严格遵守 remaining_solve_steps。"
            "如果 remaining_solve_steps 为 0，必须立刻输出 final_answer，不得继续 solve_step。"
            "如果还没有已接受的下界和上界证明，不得输出 final_answer。"
            f"\n{EXTREMAL_PROBLEM_GUIDANCE}"
            "否则请继续下一小步推理；如果已经足够作答，必须输出 "
            "{\"type\":\"final_answer\",\"answer\":\"...\",\"reasoning_summary\":\"...\"}，"
            "并确保 answer 的最终结果位于 \\boxed{} 中。"
            "box 内只能写答案值或最简数学表达式；一般函数公式优先写成 f(x)=...。"
        ),
    }


def build_force_final_answer_message(state_summary: dict[str, Any]) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            "solve_step 预算已经用完，不能再继续输出 solve_step。\n"
            "请基于当前解题状态立刻输出 final_answer JSON：\n"
            "{\"type\":\"final_answer\",\"answer\":\"...\",\"reasoning_summary\":\"...\"}\n"
            "answer 必须包含完整可判分的结论，最终结果必须位于 \\boxed{} 中。\n"
            "不要把‘Thus the answer is’、‘答案为’、引号或整句解释放进 box；"
            "一般函数公式优先写成 f(x)=...。\n"
            "当前解题状态：\n"
            + json.dumps(state_summary, ensure_ascii=False)
        ),
    }


def build_invalid_json_message(error_message: str) -> dict[str, str]:
    return build_invalid_json_retry_message(
        protocol_name="任务 JSON",
        error_message=error_message,
        allowed_formats=[
            (
                "{\"type\":\"solve_step\",\"step_summary\":\"...\","
                "\"known_facts\":[\"...\"],\"derived_results\":[\"...\"],"
                "\"remaining_tasks\":[\"...\"],\"is_ready_for_final\":false}"
            ),
            "{\"type\":\"final_answer\",\"answer\":\"...\",\"reasoning_summary\":\"...\"}",
            "{\"type\":\"tool_call\",\"tool\":\"工具名\",\"arguments\":{}}",
        ],
        extra_instructions=[
            "如果已经可以作答，必须使用 final_answer，并确保 answer 的最终结果位于 \\boxed{} 中；"
            "box 内只写答案值或最简数学表达式，一般函数公式优先使用 f(x)=...。"
        ],
    )


def build_tool_result_message(
    observation: dict[str, Any],
    tool_call_id: str,
) -> dict[str, str]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": json.dumps(observation, ensure_ascii=False),
    }
