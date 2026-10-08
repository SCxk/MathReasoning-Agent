"""Fake-runtime infrastructure measurements; never an answer-quality benchmark."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import subprocess
import time

import httpx


def wait_ready(client, seconds=60):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        response = client.get("/health/ready")
        if response.status_code == 200:
            assert response.json()["runtime_mode"] == "fake"
            assert response.json()["storage"] == "postgresql"
            return
        time.sleep(0.2)
    raise AssertionError("deployment not ready")


def completed(client, task, seconds=30):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        value = client.get(task["status_url"])
        value.raise_for_status()
        if value.json()["status"] == "succeeded":
            return value.json()
        assert value.json()["status"] not in {"failed", "cancelled"}, value.json()["error_code"]
        time.sleep(0.1)
    raise AssertionError("task did not complete")


def measure(client, session, index, release_at):
    time.sleep(max(0, release_at + index * 0.1 - time.monotonic()))
    started = time.monotonic()
    response = client.post(
        f"/v1/sessions/{session}/tasks", json={"problem": "Infrastructure fixture."}
    )
    response.raise_for_status()
    created = time.monotonic() - started
    task = response.json()
    with client.stream("GET", task["events_url"]) as stream:
        stream.raise_for_status()
        for line in stream.iter_lines():
            if line.startswith("data: "):
                assert json.loads(line[6:])["event_type"] == "task.accepted"
                first = time.monotonic() - started
                break
        else:
            raise AssertionError("empty SSE stream")
    return {"create_seconds": created, "first_status_seconds": first, "task": task}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8004")
    parser.add_argument(
        "--compose",
        action="store_true",
        help="Restart this repository's private fake worker deployment",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with httpx.Client(base_url=args.url, timeout=10) as client:
        wait_ready(client)
        sessions = []
        for _ in range(6):
            response = client.post("/v1/sessions", json={})
            response.raise_for_status()
            sessions.append(response.json()["id"])
            time.sleep(0.21)
        session = sessions[0]
        with ThreadPoolExecutor(max_workers=8) as pool:
            release_at = time.monotonic() + 0.5
            rows = list(
                pool.map(lambda i: measure(client, sessions[i % 6], i, release_at), range(30))
            )
        for row in rows:
            completed(client, row["task"])
        task = rows[0]["task"]
        replay = client.get(task["events_url"], headers={"Last-Event-ID": "1"})
        replay.raise_for_status()
        events = [
            json.loads(line[6:]) for line in replay.text.splitlines() if line.startswith("data: ")
        ]
        assert events[0]["sequence"] == 2 and events[-1]["event_type"] == "task.succeeded"
        assert [row["sequence"] for row in events] == list(range(2, len(events) + 2))
        metrics = client.get("/metrics")
        metrics.raise_for_status()
        assert "maths_task_first_status_seconds_count" in metrics.text
        assert "maths_operational_degraded" in metrics.text
        assert "maths_dispatcher_cycle_age_seconds" in metrics.text
        summary = client.get("/health/summary")
        summary.raise_for_status()
        health = summary.json()
        assert health["status"] in {"ready", "degraded"}
        assert set(health["operations"]["dispatcher"]["phases"]) == {
            "cleanup", "recovery", "dispatch", "events"
        }
        disk = health["operations"]["documents_disk"]
        assert disk is None or 0 <= disk["usage_ratio"] <= 1
        assert all(
            state["ok"] is True
            for state in health["operations"]["dispatcher"]["phases"].values()
        )
        recovery = None
        if args.compose:
            response = client.post(
                f"/v1/sessions/{session}/tasks", json={"problem": "Worker crash fixture."}
            )
            response.raise_for_status()
            recovered = response.json()
            until = time.monotonic() + 10
            while True:
                trace_response = client.get(recovered["trace_url"])
                trace_response.raise_for_status()
                trace = trace_response.json()["events"]
                if any(
                    e["event_type"] == "stage.completed" and e["stage_id"] == "retrieve"
                    for e in trace
                ):
                    break
                assert time.monotonic() < until
                time.sleep(0.1)
            started = time.monotonic()
            subprocess.run(
                ["docker", "compose", "kill", "-s", "SIGKILL", "worker"], check=True, timeout=10
            )
            subprocess.run(
                ["docker", "compose", "up", "-d", "--no-build", "worker"], check=True, timeout=15
            )
            completed(client, recovered, seconds=30)
            recovery = time.monotonic() - started
            trace = client.get(recovered["trace_url"]).json()["events"]
            assert any(e["event_type"] == "task.resumed" for e in trace)
            assert (
                sum(
                    e["event_type"] == "stage.completed" and e["stage_id"] == "retrieve"
                    for e in trace
                )
                == 1
            )
            assert recovery < 30
            wait_ready(client, seconds=15)

        def p95(key):
            return sorted(row[key] for row in rows)[math.ceil(0.95 * len(rows)) - 1]

        report = {
            "kind": "fake_infrastructure_smoke",
            "tasks": len(rows),
            "offered_rps": 10,
            "task_create_p95_seconds": p95("create_seconds"),
            "first_status_p95_seconds": p95("first_status_seconds"),
            "worker_crash_recovery_seconds": recovery,
            "completed_stage_replays": 0 if recovery is not None else None,
            "warning": "No live model, answer-quality or RAG measurement.",
        }
        print(json.dumps(report, indent=2))
        assert report["task_create_p95_seconds"] < 0.3
        assert report["first_status_p95_seconds"] < 1
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf8") as output:
                json.dump(report, output, indent=2)


if __name__ == "__main__":
    main()
