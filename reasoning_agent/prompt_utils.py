from collections.abc import Sequence


def build_invalid_json_retry_message(
    *,
    protocol_name: str,
    error_message: str,
    allowed_formats: Sequence[str] = (),
    response_excerpt: str = "",
    context_label: str = "",
    extra_instructions: Sequence[str] = (),
) -> dict[str, str]:
    lines: list[str] = [
        f"你的上一轮输出不是合法的{protocol_name}，无法被程序解析。",
    ]
    if context_label.strip():
        lines.append(context_label.strip())
    lines.append(f"解析错误：{error_message}")

    excerpt = response_excerpt.strip()
    if excerpt:
        lines.append("上一轮输出片段：")
        lines.append(excerpt)

    lines.append("请不要解释错误，不要输出 Markdown，不要输出代码块，只重新输出一个合法 JSON 对象。")

    formats = [fmt.strip() for fmt in allowed_formats if fmt and fmt.strip()]
    if formats:
        lines.append("允许的格式只有：")
        for index, fmt in enumerate(formats, start=1):
            lines.append(f"{index}. {fmt}")

    for instruction in extra_instructions:
        text = instruction.strip()
        if text:
            lines.append(text)

    return {"role": "user", "content": "\n".join(lines)}
