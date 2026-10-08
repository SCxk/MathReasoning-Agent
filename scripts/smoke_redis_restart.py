"""Verify AOF durability using a dedicated, disposable Redis process."""

import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from redis import Redis
from redis.exceptions import RedisError

from agent_platform.models import TaskStatus
from agent_platform.redis_store import RedisTaskStore


def wait_ready(client, process):
    until = time.monotonic() + 5
    while time.monotonic() < until:
        if process.poll() is not None:
            raise AssertionError("dedicated Redis exited during startup")
        try:
            client.ping()
            return
        except RedisError:
            time.sleep(.05)
    raise AssertionError("dedicated Redis startup timed out")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-server", required=True)
    parser.add_argument("--port", type=int, default=6388)
    args = parser.parse_args()
    with socket.socket() as probe:
        probe.settimeout(.2)
        if probe.connect_ex(("127.0.0.1", args.port)) == 0:
            parser.error("port is occupied; select another port")
    artifacts = Path("sample_outputs/platform_m3").resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="redis-restart-", dir=artifacts) as directory:
        command = [args.redis_server, "--bind", "127.0.0.1", "--port", str(args.port),
                   "--appendonly", "yes", "--appendfsync", "always", "--dir", directory]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = Redis(host="127.0.0.1", port=args.port, decode_responses=True,
                       socket_timeout=1, socket_connect_timeout=.2)
        try:
            wait_ready(client, process)
            store = RedisTaskStore(client)
            session = store.create_session(100)
            task, _ = store.create_task(session.id, "Durability protocol fixture.", {}, "fake", None)
            task = store.start(session.id, task.id, 1200)
            store.progress(session.id, task.id, task.generation, "solve", True, {"completed_stage": 3})
            completed, _ = store.create_task(session.id, "Completed history fixture.", {}, "fake", "history")
            running = store.start(session.id, completed.id, 1200)
            store.finish(session.id, completed.id, running.generation, TaskStatus.SUCCEEDED, "Public history fixture.")
            before = [event.model_dump(mode="json") for event in store.events_after(session.id, task.id, 0)]
            # Abruptly kill only the process created by this script, not a shared service.
            process.kill()
            process.wait(5)
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            wait_ready(client, process)
            restored = RedisTaskStore(client)
            assert restored.get_task(session.id, task.id).checkpoint == {"completed_stage": 3}
            assert restored.get_task(session.id, task.id).status == TaskStatus.RUNNING
            assert restored.get_session(session.id).messages[0].task_id == task.id
            assert [event.model_dump(mode="json") for event in restored.events_after(session.id, task.id, 0)] == before
            assert restored.list_sessions(10)["items"][0]["task_count"] == 2
            rows, cursor = restored.list_tasks(session.id, 1)
            assert rows[0].id == completed.id and rows[0].final_response == "Public history fixture."
            assert restored.list_tasks(session.id, 1, cursor)[0][0].id == task.id
            duplicate, created = restored.create_task(session.id, completed.problem, {}, "fake", "history")
            assert not created and duplicate.id == completed.id
        finally:
            if process.poll() is None:
                try:
                    client.shutdown(nosave=True)
                except RedisError:
                    pass  # Redis can close before the client's shutdown reply.
                try:
                    process.wait(5)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(5)
    print(json.dumps({"redis_abrupt_restart": "passed", "checkpoint_events_session": "preserved",
                      "durability": "AOF_appendfsync_always"}))


if __name__ == "__main__":
    main()
