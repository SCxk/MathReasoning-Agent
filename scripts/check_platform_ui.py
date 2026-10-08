"""Optional browser QA. Requires `pip install playwright` and a browser channel."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--channel", default="msedge")
    parser.add_argument("--expected-events", type=int, default=19)
    parser.add_argument("--output-dir", type=Path, default=Path("sample_outputs/platform_qa"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel, headless=True)
        for name, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844)]:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(args.url)
            page.wait_for_function("document.getElementById('session-id').textContent.length === 36")
            page.screenshot(path=str(args.output_dir / f"{name}-empty.png"), full_page=True)
            page.locator("#problem").fill("Inspect the demo workflow.")
            page.locator("#submit").click()
            page.wait_for_function("document.getElementById('cancel').disabled && !document.getElementById('answer').hidden")
            assert "Fake Runtime completed" in page.locator("#answer").inner_text()
            assert page.locator("#event-list li").count() == args.expected_events
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(args.output_dir / f"{name}-complete.png"), full_page=True)
            page.locator("#json-tab").click()
            assert "task.succeeded" in page.locator("#raw-trace").inner_text()
            assert not page.locator("#event-list").is_visible()
            page.reload()
            page.wait_for_function("!document.getElementById('answer').hidden")
            assert "Fake Runtime completed" in page.locator("#answer").inner_text()
            page.locator("#new-session").click()
            page.wait_for_function("document.getElementById('task-section').hidden")
            assert page.locator("#problem").input_value() == ""
            page.locator("#problem").fill("Exercise cancellation.")
            page.locator("#submit").click()
            page.wait_for_function("!document.getElementById('task-section').hidden")
            page.locator("#cancel").click()
            page.wait_for_function("document.getElementById('status').textContent === '已取消'")
            assert not errors, errors
            print(json.dumps({"viewport": name, "width": width, "height": height,
                              "browser_errors": errors, "workflow": "passed"}))
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
