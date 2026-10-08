from __future__ import annotations

import json
from typing import Any

from .action_registry import ActionSpec


def user_block(name: str, content: str) -> str:
    return f"<UNTRUSTED_{name}>\n{content}\n</UNTRUSTED_{name}>"


def model_preprocess_messages(problem_view: str) -> list[dict[str, str]]:
    instruction = (
        "只做数学题面预处理，不求解、不猜答案。只输出一个 JSON："
        "problem_restatement、answer_mode、known_conditions、requirements、"
        "key_variables、key_numbers、subquestions、domain_hints、complexity。"
        "subquestions 必须是 [{id,text,target}]；无法判断的字段使用 unknown 或空数组。"
    )
    return [
        {"role": "system", "content": "你是数学题面结构化预处理器。严格输出 JSON。"},
        {"role": "user", "content": instruction + "\n" + user_block("PROBLEM", problem_view)},
    ]


def profile_messages(problem_view: str, preprocess: str) -> list[dict[str, str]]:
    instruction = (
        "只做题目画像分类，不求解。只输出一个 JSON：domain、answer_mode、"
        "risk_level、complexity、reason。domain 优先使用技能目录中的英文规范名，无法确定时为 unknown。"
    )
    content = "\n\n".join([instruction, user_block("PROBLEM", problem_view), user_block("PREPROCESS", preprocess)])
    return [
        {"role": "system", "content": "你是数学题目分类器。严格输出 JSON。"},
        {"role": "user", "content": content},
    ]


def strategy_skill_messages(problem_view: str, preprocess: str, profile: str, catalog: str, actions: list[ActionSpec], strategy_cards: str = "") -> list[dict[str, str]]:
    action_text = "\n".join(f"- {item.name}: {item.description}" for item in actions)
    instruction = (
        "只做解题策略和技能筛选，不求解、不输出最终答案。只能输出一个 JSON 对象，禁止 Markdown、"
        "代码块和对象外文本。必须包含以下字段：\n"
        "- main_method：字符串，首选的通用解题方法名称，不得写最终答案。\n"
        "- backup_method：字符串，首选路线失败时的备选方法名称。\n"
        "- proof_obligations：字符串数组，列出必须分别证明的关键结论，例如下界、上界、构造或分类完备性。\n"
        "- checks：字符串数组，列出需要复核的计算、边界或前提。\n"
        "- skill_domains：字符串数组，必须来自 SKILL_INDEX 中的领域名，最多 2 个；没有合适项时 []。\n"
        "- skill_sections：字符串数组，必须是 SKILL_INDEX 中逐字出现的章节标题，最多 8 个；没有合适项时 []。\n"
        "- initial_decision：对象，绝不能是字符串或数组。它必须包含：\n"
        "  - action：字符串，必须逐字选自 ACTIONS 列表中的一个动作。\n"
        "  - target_id：字符串，当前首个子问题通常为 q1；无法细分时写 q1。\n"
        "  - goal：非空字符串，说明本动作要完成的一个具体数学推进，不能写‘分析题目’等空泛表述。\n"
        "  - required_fact_ids：字符串数组；首步通常为 []，只能引用已接受事实的 ID。\n"
        "  - success_condition：非空字符串，说明何种可核验结果代表本动作完成。\n"
        "  - branch_hint：可选字符串，只有需要分支时填写，否则省略。\n"
        "请严格遵循此模板（字段值仅为格式示例，不得照抄方法或结论）：\n"
        '{"main_method":"...","backup_method":"...","proof_obligations":["..."],"checks":["..."],'
        '"skill_domains":["..."],"skill_sections":["..."],"initial_decision":{"action":"derive",'
        '"target_id":"q1","goal":"推出一个可验证的局部结论","required_fact_ids":[],"success_condition":"得到并核验该局部结论"}}'
    )
    content = "\n\n".join([
        instruction,
        user_block("PROBLEM", problem_view),
        user_block("PREPROCESS", preprocess),
        user_block("PROFILE", profile),
        user_block("SKILL_INDEX", catalog),
        user_block("ACTIONS", action_text),
    ])
    if strategy_cards:
        content += "\n\n" + user_block("STRATEGY_CASES", strategy_cards)
    return [
        {"role": "system", "content": "你是数学解题策略和技能检索规划器。严格输出 JSON。"},
        {"role": "user", "content": content},
    ]


def bootstrap_messages(problem_view: str, actions: list[ActionSpec], catalog: str) -> list[dict[str, str]]:
    action_text = "\n".join(f"- {item.name}: {item.description}" for item in actions)
    instruction = (
        "你只负责选择第一个数学动作，不要给出完整解答或最终答案。返回一个 JSON 对象，包含 "
        "domain、answer_mode、risk_level、skill_domains、skill_sections、initial_decision。"
        "initial_decision 必含 action、target_id、goal、required_fact_ids、success_condition。"
        "domain 必须是技能目录中的英文名或 unknown；skill_domains 至多2项，skill_sections至多8项。"
    )
    content = "\n\n".join([instruction, user_block("PROBLEM", problem_view), user_block("SKILL_CATALOG", catalog), user_block("ACTIONS", action_text)])
    return [{"role": "system", "content": "你是数学动作规划器。严格输出 JSON。"}, {"role": "user", "content": content}]


def planner_messages(problem_view: str, target: str, accepted: str, failures: str, actions: list[ActionSpec], profile: str = "", strategy: str = "") -> list[dict[str, str]]:
    payload = {"target": target, "accepted": accepted, "failures": failures, "actions": [{"name": item.name, "description": item.description} for item in actions]}
    instruction = "只选择一个下一动作并输出 JSON：action、target_id、goal、required_fact_ids、success_condition。不得求解整题或输出候选答案。"
    blocks = [instruction, user_block("STATE", json.dumps(payload, ensure_ascii=False))]
    if profile:
        blocks.append(user_block("PROFILE", profile))
    if strategy:
        blocks.append(user_block("STRATEGY", strategy))
    return [{"role": "system", "content": "你是数学动作规划器。严格输出 JSON。"}, {"role": "user", "content": "\n\n".join(blocks)}]


def executor_messages(domain: str, action: str, goal: str, problem: str, accepted: str, failures: str, skills: str, repair: str = "", preprocess: str = "", profile: str = "", strategy: str = "", strategy_cases: str = "") -> list[dict[str, str]]:
    system = f"你是{domain}领域的数学专家。" if domain != "unknown" else "你是数学专家。"
    instruction = (
        f"你当前只能执行动作 {action}，目标是：{goal}。不要代替 Finalizer 写完整整题答案。"
        "给出可审核的简洁数学正文；若已得到该问的直接结论，可在末尾给出 <ACTION_RESULT>{\"answer\":\"...\",\"covers\":[\"q1\"]}</ACTION_RESULT>。"
    )
    if action in {"negate", "induct", "classify"}:
        instruction = (
            f"你当前只能设计 {action} 的有限分支方案，不得直接宣称整题完成。"
            "严格输出 JSON：{\"branches\":[{\"conditions\":\"...\",\"goal\":\"...\"}]}；"
            "归纳必须含基例与归纳步骤，反证必须给反设和矛盾目标。"
        )
    parts = [instruction, user_block("PROBLEM", problem), user_block("PREPROCESS", preprocess), user_block("PROFILE", profile), user_block("STRATEGY", strategy), user_block("ACCEPTED", accepted), user_block("FAILURES", failures), user_block("SKILLS", skills)]
    if strategy_cases:
        parts.append(user_block("STRATEGY_CASES", strategy_cases))
    if repair:
        parts.append(user_block("REPAIR", repair))
    return [{"role": "system", "content": system}, {"role": "user", "content": "\n\n".join(parts)}]


def reflector_messages(goal: str, problem: str, output: str, accepted: str) -> list[dict[str, str]]:
    instruction = (
        "审核一个局部动作结果。只输出 JSON：verdict (accept/repair/reject_route)、accepted_claims（字符串列表）、"
        "covered_subquestion_ids、first_fatal_error、repair_instruction、invalidated_claim_ids。"
        "只接受本次输出明确支持的结论；不要重写整题答案。"
    )
    content = "\n\n".join([instruction, user_block("GOAL", goal), user_block("PROBLEM", problem), user_block("OUTPUT", output), user_block("ACCEPTED", accepted)])
    return [{"role": "system", "content": "你是严谨的数学局部审核器。严格输出 JSON。"}, {"role": "user", "content": content}]


def finalizer_messages(problem: str, candidates: list[dict[str, Any]], claims: str) -> list[dict[str, str]]:
    instruction = "仅使用原题、已支持候选答案和已审核结论回答所有问项。证明题保留必要证明。不要输出 JSON、计划或状态。"
    content = "\n\n".join([instruction, user_block("PROBLEM", problem), user_block("SUPPORTED_CANDIDATES", json.dumps(candidates, ensure_ascii=False)), user_block("ACCEPTED_CLAIMS", claims)])
    return [{"role": "system", "content": "你是数学答案整理器。"}, {"role": "user", "content": content}]


def emergency_guess_messages(problem: str, candidates: list[dict[str, Any]], claims: str, strategy: str, node_material: str) -> list[dict[str, str]]:
    instruction = (
        "这是一次最佳努力收束，不要输出 JSON、计划或状态。综合原题、已有候选、已审核结论、策略和节点材料，"
        "沿最可信的一条路线给出最可能的数学答案。可以简短说明依据；即使证据不完整，也必须给出明确的数值、"
        "表达式、集合或结论，并在最后使用 \\boxed{}。不要返回‘无法确定唯一答案’。"
    )
    content = "\n\n".join([
        instruction,
        user_block("PROBLEM", problem),
        user_block("SUPPORTED_CANDIDATES", json.dumps(candidates, ensure_ascii=False)),
        user_block("ACCEPTED_CLAIMS", claims),
        user_block("STRATEGY", strategy),
        user_block("NODE_MATERIAL", node_material),
    ])
    return [{"role": "system", "content": "你是数学题的最佳努力答案收束器。"}, {"role": "user", "content": content}]
