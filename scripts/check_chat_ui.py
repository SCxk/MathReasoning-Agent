"""Chat browser QA: real Fake-runtime APIs; explicit synthetic answer-rendering fixtures."""

import argparse
import json
from pathlib import Path
import re

import httpx
from playwright.sync_api import expect, sync_playwright


RENDER_FIXTURE = r"""### 渲染测试结果（非模型解答）

行内公式：$a^2+b^2=c^2$，以及 \(x=\frac{1}{2}\)。

\[
\int_0^1 x^2\,dx=\frac{1}{3}
\]

| 项目 | 状态 |
| --- | --- |
| Markdown | 渲染检查 |
| 公式 | 渲染检查 |

```python
value = "rendering fixture"
```

<script>window.chatInjected = true</script>

![external](https://private.invalid/never-load)
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8006/chat/")
    parser.add_argument("--channel", default="msedge")
    parser.add_argument("--output-dir", type=Path, default=Path("sample_outputs/chat_qa"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=5) as client:
        health = client.get(args.url.split("/chat")[0] + "/health/ready").json()
        assert health["runtime_mode"] == "fake", "QA must never submit live-model requests"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel, headless=True)
        for name, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844), ("tablet", 1024, 768), ("narrow", 320, 740)]:
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            errors, external = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: external.append(request.url) if "private.invalid" in request.url else None)
            page.goto(args.url)
            expect(page.get_by_test_id("runtime-mode")).to_have_text("演示运行时")
            modes = page.get_by_role("combobox", name="解答方式")
            expect(modes).to_be_enabled()
            expect(modes).to_have_value("auto")
            for style in ("answer", "brief", "detailed", "auto"):
                modes.select_option(style)
                expect(modes).to_have_value(style)
            page.screenshot(path=str(args.output_dir / f"{name}-empty.png"))

            def new_chat():
                if width <= 760:
                    page.get_by_role("button", name="会话列表", exact=True).click()
                    page.get_by_role("dialog").get_by_role("button", name="新建会话").click()
                else:
                    page.get_by_role("button", name="新建会话").click()

            def progress():
                if width <= 1190:
                    page.get_by_role("button", name="执行进度", exact=True).click()

            def close_progress():
                if width <= 1190:
                    page.get_by_role("button", name="关闭面板").click()

            new_chat()
            expect(page.get_by_role("heading", name="MathReasoning-Agent", exact=True)).to_be_visible()

            def current_task():
                session = page.evaluate("localStorage.getItem('maths-chat-selected-v1')")
                if session:
                    rows = page.request.get(args.url.split("/chat")[0] + f"/v1/sessions/{session}/tasks").json()["items"]
                    return session, rows[0]["id"]
                entry = page.evaluate("JSON.parse(localStorage.getItem('maths-chat-history-v1'))[0]")
                return entry["id"], entry["tasks"][-1]["id"]

            question = page.get_by_role("textbox", name="数学问题")
            question.fill("界面协议测试：检查任务进度与最终结果。")
            # IME composition must not submit a Chinese input in progress.
            question.evaluate("el => el.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', isComposing:true, bubbles:true}))")
            assert page.get_by_test_id("exchange").count() == 0
            question.press("Shift+Enter")
            assert "\n" in question.input_value()
            question.press("Enter")
            expect(modes).to_be_disabled()
            progress()
            expect(page.locator('[data-testid="task-status"]:visible')).to_have_text("正在解题")
            page.screenshot(path=str(args.output_dir / f"{name}-progress.png"))
            close_progress()
            expect(page.get_by_test_id("answer")).to_contain_text("Fake Runtime completed", timeout=15000)
            assert page.get_by_role("button", name="取消任务", exact=True).count() == 0

            session, task_id = current_task()
            path = f"/v1/sessions/{session}/tasks/{task_id}"
            actual = page.request.get(args.url.split("/chat")[0] + path).json()
            assert actual["response_style"] == "auto"
            fixture = {**actual, "final_response": RENDER_FIXTURE}
            history_pattern = re.compile(re.escape(f"/v1/sessions/{session}/tasks") + r"\?")
            def fixture_history(route):
                response = route.fetch()
                data = response.json()
                data["items"] = [{**item, **fixture} if item["id"] == task_id else item for item in data["items"]]
                route.fulfill(response=response, json=data)
            page.route(history_pattern, fixture_history)
            page.route(re.compile(re.escape(path) + r"$"), lambda route: route.fulfill(json=fixture))
            page.reload()
            expect(page.get_by_test_id("answer")).to_contain_text("渲染测试结果（非模型解答）")
            expect(page.locator('[data-testid="answer"] .katex')).to_have_count(3)
            assert page.locator('[data-testid="answer"] .katex-display').count() == 1
            assert page.get_by_test_id("answer").locator("table").count() == 1
            assert page.evaluate("window.chatInjected !== true")
            assert not external
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(args.output_dir / f"{name}-math.png"))
            if width == 1440:
                context.grant_permissions(["clipboard-read", "clipboard-write"])
                page.get_by_role("button", name="复制答案").click()
                page.wait_for_function("text => navigator.clipboard.readText().then(value => value === text)", arg=RENDER_FIXTURE)
            page.unroute(re.compile(re.escape(path) + r"$"))

            fixture["final_response"] = r"\boxed{1. $u=\frac{4}{7}$; 2. $\{a,b\}$}"
            page.route(re.compile(re.escape(path) + r"$"), lambda route: route.fulfill(json=fixture))
            page.reload()
            expect(page.locator('[data-testid="answer"] .katex')).to_have_count(2)
            expect(page.locator('[data-testid="answer"] .katex-error')).to_have_count(0)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(args.output_dir / f"{name}-legacy-box.png"))
            page.unroute(re.compile(re.escape(path) + r"$"))

            fixture["final_response"] = r"\boxed{\text{$x$}}"
            page.route(re.compile(re.escape(path) + r"$"), lambda route: route.fulfill(json=fixture))
            page.reload()
            expect(page.locator('[data-testid="answer"] .katex')).to_have_count(1)
            expect(page.locator('[data-testid="answer"] .katex-error')).to_have_count(0)
            page.unroute(re.compile(re.escape(path) + r"$"))

            fixture["final_response"] = RENDER_FIXTURE + "\n\n\\[" + "+".join(f"x_{{{i}}}" for i in range(60)) + "\\]"
            page.route(re.compile(re.escape(path) + r"$"), lambda route: route.fulfill(json=fixture))
            page.reload()
            expect(page.locator('[data-testid="answer"] .katex')).to_have_count(4)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(args.output_dir / f"{name}-wide-formula.png"))
            page.unroute(re.compile(re.escape(path) + r"$"))
            page.unroute(history_pattern)

            new_chat()
            question.fill("界面协议测试：取消尚未完成的任务。")
            page.get_by_role("button", name="发送问题", exact=True).click()
            page.locator(".composer").get_by_role("button", name="取消任务", exact=True).click()
            expect(page.locator(".assistant-message")).to_contain_text("任务已取消", timeout=10000)
            assert page.get_by_test_id("answer").count() == 0
            page.reload()
            expect(page.locator(".assistant-message")).to_contain_text("任务已取消", timeout=10000)
            page.screenshot(path=str(args.output_dir / f"{name}-cancelled.png"))

            # Drop the first SSE connection; the client must reconnect with its last cursor.
            new_chat()
            connections = []

            def drop_once(route):
                connections.append(route.request.url)
                if len(connections) == 1:
                    route.abort("failed")
                else:
                    route.continue_()

            page.route("**/events?*", drop_once)
            question.fill("界面协议测试：断线后继续观察任务。")
            page.get_by_role("button", name="发送问题", exact=True).click()
            expect(page.get_by_test_id("answer")).to_contain_text("Fake Runtime completed", timeout=15000)
            assert len(connections) >= 2
            assert "after=" in connections[-1]
            page.unroute("**/events?*")
            for style in ("answer", "brief", "detailed"):
                new_chat()
                modes.select_option(style)
                question.fill("界面协议测试：核对解答方式参数。")
                page.get_by_role("button", name="发送问题", exact=True).click()
                expect(page.get_by_test_id("answer")).to_contain_text("Fake Runtime completed", timeout=15000)
                saved_session, saved_id = current_task()
                saved = page.request.get(args.url.split("/chat")[0]
                    + f"/v1/sessions/{saved_session}/tasks/{saved_id}").json()
                assert saved["response_style"] == style
                expect(modes).to_be_enabled()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors, errors
            print(json.dumps({"viewport": name, "workflow": "passed", "browser_errors": errors,
                              "math_source": "synthetic renderer fixture, not model output"}))
            context.close()
        browser.close()


if __name__ == "__main__":
    main()
