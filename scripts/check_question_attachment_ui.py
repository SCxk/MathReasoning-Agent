"""Actual isolated question parsing and durable dispatch, with Fake-only solving."""

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright
import psutil
from redis import Redis

from smoke_platform_m5 import pdf_file


TEXT = b"# Exercise sheet\n\n## Question 1\nSolve $x+1=3$.\n\n## Question 2\nCompute $2^3$.\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-url-env", default="MATHS_CHAT_REDIS_URL")
    parser.add_argument("--port", type=int, default=8008)
    args = parser.parse_args()
    with socket.socket() as probe:
        assert probe.connect_ex(("127.0.0.1", args.port)) != 0, "QA must not replace another service"
    output = Path("sample_outputs/question_attachment_qa")
    output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="run-", dir=output)).resolve()
    namespace = "question_qa:" + uuid4().hex
    redis = Redis.from_url(os.environ[args.redis_url_env], decode_responses=True)
    base = f"http://127.0.0.1:{args.port}"
    server = None
    log = (root / "server.log").open("w", encoding="utf-8")

    def stop():
        nonlocal server
        if server:
            try:
                parent = psutil.Process(server.pid)
                processes = parent.children(recursive=True) + [parent]
                for process in processes:
                    try:
                        process.terminate()
                    except psutil.NoSuchProcess:
                        pass
                _, pending = psutil.wait_procs(processes, timeout=5)
                for process in pending:
                    process.kill()
                psutil.wait_procs(pending, timeout=5)
            except psutil.NoSuchProcess:
                pass
            server.wait(10)
            server = None

    def start():
        nonlocal server
        server = subprocess.Popen([sys.executable, "-m", "agent_platform", "--runtime", "fake", "--port", str(args.port),
            "--question-dir", str(root / "questions"), "--redis-url-env", args.redis_url_env, "--namespace", namespace],
            stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        end = time.monotonic() + 30
        while time.monotonic() < end:
            if server.poll() is not None:
                raise RuntimeError("private question API failed to start")
            try:
                response = httpx.get(base + "/health/ready", timeout=2)
                if response.status_code == 200:
                    health = response.json()
                    assert health["runtime_mode"] == "fake" and health["restart_durable"] and health["question_attachments"]
                    assert health["question_submission"] == "explicit_send"
                    return
            except httpx.HTTPError:
                pass
            time.sleep(.2)
        raise TimeoutError("question API readiness timeout")

    try:
        start()
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            for name, width, height in [("desktop",1440,1000),("mobile",390,844),("tablet",1024,768),("narrow",320,740)]:
                context = browser.new_context(viewport={"width":width,"height":height}, accept_downloads=True)
                page = context.new_page()
                errors = []
                document_requests = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: document_requests.append(request.url)
                        if "/documents" in request.url else None)
                page.goto(base + "/chat/")
                expect(page.get_by_test_id("runtime-mode")).to_have_text("演示运行时")
                expect(page.get_by_role("button", name="上传附件", exact=True)).to_have_count(0)
                expect(page.get_by_text("参考附件", exact=True)).to_have_count(0)
                def new_chat():
                    if width <= 760:
                        page.get_by_role("button", name="会话列表", exact=True).click()
                        page.get_by_role("dialog").get_by_role("button", name="新建会话").click()
                    else:
                        page.get_by_role("button", name="新建会话").click()
                    expect(page.get_by_test_id("question-result")).to_have_count(0)
                new_chat()
                expect(page.get_by_role("button", name="文字提问", exact=True)).to_have_count(0)
                expect(page.get_by_role("button", name="题目附件", exact=True)).to_have_count(0)
                expect(page.get_by_role("button", name="发送问题", exact=True)).to_be_disabled()
                page.get_by_role("textbox", name="数学问题").press("Enter")
                expect(page.get_by_role("button", name="上传题目附件", exact=True)).to_be_enabled()
                expect(page.get_by_role("textbox", name="数学问题")).to_have_count(1)
                expect(page.locator(".message-scroll").get_by_role("button", name="上传题目附件", exact=True)).to_have_count(0)
                upload_button = page.get_by_test_id("question-upload-slot").get_by_role("button", name="上传题目附件", exact=True)
                expect(upload_button).to_be_visible()
                upload_box = upload_button.bounding_box()
                composer_box = page.get_by_role("textbox", name="数学问题").bounding_box()
                assert upload_box["y"] + upload_box["height"] <= composer_box["y"]
                picker = page.get_by_label("题目附件文件", exact=True)
                with page.expect_file_chooser() as choosing:
                    upload_button.click()
                choosing.value.set_files({"name":"exercise.md","mimeType":"","buffer":TEXT})
                expect(page.get_by_test_id("question-result")).to_have_count(2, timeout=30000)
                expect(page.get_by_test_id("batch-status")).to_have_text("待提交")
                session = page.evaluate("localStorage.getItem('maths-chat-selected-v1')")
                batches = page.request.get(base + f"/v1/sessions/{session}/question-batches").json()["items"]
                identifier = batches[0]["id"]
                route = base + f"/v1/sessions/{session}/question-batches/{identifier}"
                preview = page.request.get(route).json()
                assert page.request.get(base + f"/v1/sessions/{session}/tasks").json()["items"] == []
                expect(page.get_by_test_id("question-answer")).to_have_count(0)
                composer = page.get_by_role("textbox", name="数学问题")
                expect(page.get_by_test_id("pending-attachment")).to_contain_text("exercise.md")
                expect(page.get_by_role("button", name="发送问题", exact=True)).to_be_enabled()
                if name == "desktop":
                    stop()
                    start()
                    assert page.request.get(route).json() == preview
                    assert page.request.get(base + f"/v1/sessions/{session}/tasks").json()["items"] == []
                    page.reload()
                    expect(page.get_by_test_id("pending-attachment")).to_contain_text("exercise.md")
                composer.fill("Explain each question.")
                composer.dispatch_event("keydown", {"key": "Enter", "code": "Enter", "isComposing": True, "keyCode": 229})
                assert page.request.get(base + f"/v1/sessions/{session}/tasks").json()["items"] == []
                page.screenshot(path=str(root / f"{name}-ready.png"), full_page=True)
                composer.press("Shift+Enter")
                expect(composer).to_have_value("Explain each question.\n")
                composer.press("Enter")
                expect(page.get_by_test_id("question-answer")).to_have_count(2, timeout=30000)
                expect(page.get_by_test_id("batch-status")).to_have_text("处理结束", timeout=15000)
                expect(page.get_by_test_id("pending-attachment")).to_have_count(0)
                expect(page.get_by_role("button", name="发送问题", exact=True)).to_be_disabled()
                expect(page.get_by_test_id("question-answer").first).to_contain_text("Fake Runtime completed")
                assert page.locator(".question-stem .katex").count() == 2
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(root / f"{name}-completed.png"), full_page=True)
                session = page.evaluate("localStorage.getItem('maths-chat-selected-v1')")
                batches = page.request.get(base + f"/v1/sessions/{session}/question-batches").json()["items"]
                identifier = batches[0]["id"]
                route = base + f"/v1/sessions/{session}/question-batches/{identifier}"
                before = page.request.get(route).json()
                assert before["user_instruction"] == "Explain each question."
                assert before["question_count"] == before["counts"]["succeeded"] == 2
                for question in before["questions"]:
                    assert question["task"]["references"] == []
                with page.expect_download() as downloaded:
                    page.get_by_role("button", name="导出题目结果", exact=True).click()
                download = downloaded.value
                download.save_as(str(root / f"{name}-results.md"))
                assert "Fake Runtime completed" in (root / f"{name}-results.md").read_text(encoding="utf-8")
                picker.set_input_files({"name":"exercise.md","mimeType":"","buffer":TEXT})
                page.wait_for_timeout(1000)
                assert len(page.request.get(base + f"/v1/sessions/{session}/tasks").json()["items"]) == 2
                if name == "desktop":
                    stop()
                    start()
                    assert page.request.get(route).json() == before
                page.evaluate("localStorage.clear()")
                page.reload()
                expect(page.get_by_test_id("question-answer")).to_have_count(2)
                expect(page.get_by_test_id("exchange")).to_have_count(0)
                # A normal text question still works alongside finished batch history.
                page.get_by_role("textbox", name="数学问题").fill("Synthetic text-task protocol check.")
                page.get_by_role("button", name="发送问题", exact=True).click()
                expect(page.get_by_test_id("answer")).to_have_count(1, timeout=15000)
                new_chat()
                pdf = pdf_file()
                picker.set_input_files({"name":"geometry.pdf","mimeType":"application/pdf","buffer":pdf.file.read()})
                expect(page.get_by_test_id("batch-status")).to_have_text("待提交", timeout=30000)
                expect(page.get_by_test_id("question-answer")).to_have_count(0)
                expect(page.get_by_role("textbox", name="数学问题")).to_have_value("")
                page.get_by_role("button", name="发送问题", exact=True).click()
                expect(page.get_by_test_id("question-answer")).to_have_count(1, timeout=30000)
                expect(page.get_by_test_id("question-result")).to_contain_text("第 1 页")
                pdf_session = page.evaluate("localStorage.getItem('maths-chat-selected-v1')")
                pdf_batch = page.request.get(base + f"/v1/sessions/{pdf_session}/question-batches").json()["items"][0]
                assert pdf_batch["user_instruction"] == ""
                new_chat()
                picker.set_input_files({"name":"cancel.md","mimeType":"","buffer":TEXT * 1 + b"\n## Question 3\nCompute another value."})
                expect(page.get_by_test_id("batch-status")).to_have_text("待提交", timeout=30000)
                page.get_by_role("button", name="移除本次附件", exact=True).click()
                expect(page.get_by_test_id("pending-attachment")).to_have_count(0)
                page.get_by_role("textbox", name="数学问题").fill("Unattached text fixture.")
                page.get_by_role("textbox", name="数学问题").press("Enter")
                expect(page.get_by_test_id("answer")).to_have_count(1, timeout=15000)
                expect(page.get_by_test_id("batch-status")).to_have_text("待提交")
                expect(page.get_by_test_id("question-answer")).to_have_count(0)
                page.get_by_role("button", name="cancel.md", exact=False).click()
                expect(page.get_by_test_id("pending-attachment")).to_contain_text("cancel.md")
                expect(page.get_by_role("button", name="取消整批", exact=True)).to_be_visible()
                page.get_by_role("button", name="取消整批", exact=True).click()
                expect(page.get_by_test_id("batch-status")).to_have_text("已取消", timeout=15000)
                cancelled_session = page.evaluate("localStorage.getItem('maths-chat-selected-v1')")
                assert page.request.get(base + f"/v1/sessions/{cancelled_session}/question-batches/{identifier}").status == 404
                page.reload()
                expect(page.get_by_test_id("batch-status")).to_have_text("已取消")
                assert not errors, errors
                assert not document_requests, document_requests
                print(json.dumps({"viewport":name,"status":"passed","parser":"actual_isolated_pdf_markdown",
                                  "generation":"fake_only","live_model_calls":0}), flush=True)
                context.close()
            browser.close()
        print(str(root), flush=True)
    finally:
        stop()
        log.close()
        keys = list(redis.scan_iter(match=namespace + ":*"))
        if keys:
            redis.delete(*keys)
        redis.close()


if __name__ == "__main__":
    main()
