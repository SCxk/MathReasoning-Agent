"""Exercise real HTTP/SSE disconnect and replay without a model API."""

import argparse
import json
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    with httpx.Client(base_url=args.url, timeout=10) as client:
        health = client.get("/health/ready")
        health.raise_for_status()
        assert health.json()["runtime_mode"] == "fake", "smoke test expects Fake Runtime"
        session = client.post("/v1/sessions", json={})
        session.raise_for_status()
        response = client.post(f"/v1/sessions/{session.json()['id']}/tasks",
                               json={"problem": "Exercise the demo lifecycle."})
        response.raise_for_status()
        task = response.json()
        with client.stream("GET", task["events_url"]) as stream:
            stream.raise_for_status()
            for line in stream.iter_lines():
                if line.startswith("data: "):
                    first = json.loads(line[6:])
                    assert first["event_type"] == "task.accepted"
                    break
        # Closing the first stream must not cancel task execution.
        until = time.monotonic() + 10
        while True:
            status = client.get(task["status_url"]).json()
            if status["status"] in {"succeeded", "failed", "cancelled"}:
                break
            assert time.monotonic() < until, "task did not finish"
            time.sleep(.05)
        assert status["status"] == "succeeded"
        replay = client.get(task["events_url"], headers={"Last-Event-ID": str(first["sequence"])})
        replay.raise_for_status()
        events = [json.loads(line[6:]) for line in replay.text.splitlines() if line.startswith("data: ")]
        assert events[0]["sequence"] == first["sequence"] + 1
        assert events[-1]["event_type"] == "task.succeeded"
        print(json.dumps({"http_sse_smoke": "passed", "replayed_events": len(events),
                          "runtime_mode": "fake"}))


if __name__ == "__main__":
    main()
