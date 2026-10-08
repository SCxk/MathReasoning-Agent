"""Private Fake-only HTTP/browser history restart smoke; never calls a model."""

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright
from redis import Redis

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_platform.models import TaskStatus
from agent_platform.redis_store import RedisTaskStore


def wait_ready(base, process):
    until = time.monotonic() + 15
    while time.monotonic() < until:
        if process.poll() is not None:
            raise AssertionError("private history API exited")
        try:
            value = httpx.get(base + "/health/ready", timeout=1)
            if value.status_code == 200:
                assert value.json()["runtime_mode"] == "fake"
                assert value.json()["restart_durable"]
                return
        except httpx.HTTPError:
            pass
        time.sleep(.1)
    raise AssertionError("private history API startup timed out")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-url-env", required=True)
    parser.add_argument("--port", type=int, default=8008)
    parser.add_argument("--output-dir", type=Path, default=Path("sample_outputs/history_restart_qa"))
    args = parser.parse_args()
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", args.port)) == 0:
            parser.error("port occupied; private smoke cannot replace an existing service")
    namespace = "history_qa:" + uuid4().hex
    client = Redis.from_url(os.environ[args.redis_url_env], decode_responses=True,
                            socket_timeout=1, socket_connect_timeout=1)
    store = RedisTaskStore(client, namespace=namespace)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "agent_platform", "--port", str(args.port),
               "--redis-url-env", args.redis_url_env, "--namespace", namespace]
    base = f"http://127.0.0.1:{args.port}"
    process = None
    try:
        for index in range(32):
            session = store.create_session(0)
            count = 25 if index == 31 else 1
            for number in range(count):
                task, _ = store.create_task(session.id, f"History fixture {index}/{number}", {}, "fake", str(number))
                running = store.start(session.id, task.id, 1200)
                store.progress(session.id, task.id, running.generation, "solve", True, {"fixture": True})
                store.finish(session.id, task.id, running.generation, TaskStatus.SUCCEEDED, f"History fixture answer {number}")
        with (args.output_dir / "api.log").open("wb") as log:
            process = subprocess.Popen(command, stdout=log, stderr=log)
            wait_ready(base, process)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                try:
                    for name, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844)]:
                        context = browser.new_context(viewport={"width": width, "height": height})
                        page = context.new_page()
                        page.goto(base + "/chat/")
                        expect(page.get_by_test_id("exchange")).to_have_count(20)
                        page.get_by_role("button", name="更早的问题", exact=True).click()
                        expect(page.get_by_test_id("exchange")).to_have_count(25)
                        expect(page.get_by_test_id("answer").last).to_have_text("History fixture answer 24已完成")
                        assert page.evaluate("localStorage.getItem('maths-chat-history-v1') === null")
                        if width <= 760:
                            page.get_by_role("button", name="会话列表", exact=True).click()
                        expect(page.locator(".session-item:visible")).to_have_count(30)
                        page.get_by_role("button", name="更多会话", exact=True).click()
                        expect(page.locator(".session-item:visible")).to_have_count(32)
                        if width <= 760:
                            page.get_by_role("button", name="关闭面板", exact=True).click()
                        page.screenshot(path=str(args.output_dir / f"{name}-history.png"))
                        page.evaluate("localStorage.clear()")
                        page.reload()
                        expect(page.get_by_test_id("exchange")).to_have_count(20)
                        expect(page.get_by_test_id("answer").last).to_contain_text("History fixture answer 24")
                        # Restart only this smoke's API; persisted answers do not require model replay.
                        process.terminate()
                        process.wait(10)
                        process = subprocess.Popen(command, stdout=log, stderr=log)
                        wait_ready(base, process)
                        page.evaluate("localStorage.clear()")
                        page.reload()
                        expect(page.get_by_test_id("answer").last).to_contain_text("History fixture answer 24")
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                        context.close()
                        print(json.dumps({"viewport": name, "history_pagination": "passed",
                                          "browser_storage_clear": "passed", "api_restart": "passed"}))
                finally:
                    browser.close()
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(10)
        # Only this random test namespace is removed; shared Redis remains running.
        keys = list(client.scan_iter(match=namespace + ":*", count=100))
        if keys:
            client.delete(*keys)
        client.close()


if __name__ == "__main__":
    main()
