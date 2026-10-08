"""Kill/restart a graph worker against real Redis; protocol stubs, not evaluation."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

# Also supports direct execution from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from redis import Redis

from agent_platform.graph_runtime import LangGraphRuntime
from agent_platform.models import TaskStatus
from agent_platform.redis_store import RedisTaskStore
from agent_platform.runtime import RuntimeContext
from agent_platform.service import TaskService
from reasoning_agent.custom.config import AgentConfig


class ProtocolStubClient:
    """Fixed protocol fixtures solely for failure-injection infrastructure QA."""

    def __init__(self, resume=False):
        self.responses = (
            ['{"verdict":"pass"}', '{"verdict":"pass"}'] if resume else [
                '{"domain":"linear_algebra","answer_mode":"computation"}',
                '{"risk_level":"high"}',
                "## 问题分析\nProtocol fixture.\n## 详细解题步骤\nFixture derivation.\n"
                "## 最终答案\n\\boxed{2}\n## 关键验证点\nFixture validation.",
                '{"verdict":"pass"}', '{"verdict":"pass"}',
            ]
        )
        self.count = 0

    def chat(self, messages, temperature, max_tokens, request_timeout=None, **kwargs):
        response = self.responses[self.count]
        self.count += 1
        return {"content": response, "usage": {"total_tokens": 1}}


def runtime(resume=False):
    return LangGraphRuntime(ProtocolStubClient(resume), AgentConfig(
        custom2_solver_protocol="staged", staged_strategy_retrieval_enabled=False,
        staged_strategy_model_enabled=True, staged_compact_reasoning_only=False,
        staged_solver_compressed_retry_enabled=False,
    ))


async def child(args, store):
    agent = runtime()
    task = store.start(args.session, args.task, 1200)
    def progress(stage, completed, checkpoint):
        store.progress(task.session_id, task.id, task.generation, stage, completed, checkpoint)
        if stage == "solve" and completed:
            # A hard process exit skips lifespan cleanup, leaving a real lease.
            os._exit(23)
    ctx = RuntimeContext(task.id, task.session_id, task.problem, task.metadata, task.memory,
                         task.checkpoint, progress, deadline_at=task.deadline_at,
                         record=lambda stage, kind, data: store.record(
                             task.session_id, task.id, task.generation, stage, kind, data))
    await agent.run(ctx)


async def recover(store, session, task_id):
    service = TaskService(store, runtime(resume=True))
    started = time.monotonic()
    await service.start()
    try:
        while time.monotonic() - started < 30:
            task = store.get_task(session, task_id)
            if task.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED}:
                assert task.status == TaskStatus.SUCCEEDED, task.error_code
                return time.monotonic() - started
            await asyncio.sleep(.1)
        raise AssertionError("recovery exceeded 30 seconds")
    finally:
        await service.stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url-env", default="MATHS_REDIS_URL")
    parser.add_argument("--namespace")
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--session")
    parser.add_argument("--task")
    args = parser.parse_args()
    url = os.environ.get(args.url_env)
    if not url:
        parser.error("Redis URL environment variable is required")
    args.namespace = args.namespace or "maths:m3smoke:" + uuid4().hex
    store = RedisTaskStore(Redis.from_url(url, decode_responses=True,
                                        socket_timeout=1, socket_connect_timeout=1), namespace=args.namespace)
    if args.child:
        asyncio.run(child(args, store))
        return
    session = store.create_session(0)
    task, _ = store.create_task(session.id, "Infrastructure protocol fixture.", {}, "langgraph_staged", None)
    process = subprocess.run([
        sys.executable, str(Path(__file__).resolve()), "--child", "--url-env", args.url_env,
        "--namespace", args.namespace, "--session", session.id, "--task", task.id,
    ], capture_output=True, text=True, timeout=20)
    assert process.returncode == 23, "worker did not exit at the persisted solve boundary"
    assert store.get_task(session.id, task.id).checkpoint["next_stage"] == "tool"
    # New client, service, graph and store objects; no memory from the child.
    reopened = RedisTaskStore(Redis.from_url(url, decode_responses=True), namespace=args.namespace)
    seconds = asyncio.run(recover(reopened, session.id, task.id))
    events = reopened.events_after(session.id, task.id, 0)
    assert len([event for event in events if event.event_type == "model.completed"]) == 5
    assert len([event for event in events if event.event_type == "stage.completed" and event.stage_id == "solve"]) == 1
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    print(json.dumps({"process_crash_recovery": "passed", "recovery_seconds": round(seconds, 3),
                      "completed_solve_replays": 0, "model_client": "protocol_stub",
                      "live_model_quality_measured": False}))


if __name__ == "__main__":
    main()
