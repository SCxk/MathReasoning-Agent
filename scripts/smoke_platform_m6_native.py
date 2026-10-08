"""Own and kill only private fixture subprocesses; use a scratch PostgreSQL URL."""

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from redis import Redis
from sqlalchemy.schema import DropSchema

from agent_platform.database import database, migrate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url-env", default="MATHS_TEST_DATABASE_URL")
    parser.add_argument("--redis-url-env", default="MATHS_TEST_REDIS_URL")
    args = parser.parse_args()
    with socket.socket() as check:
        if check.connect_ex(("127.0.0.1", 8004)) == 0:
            parser.error("fixture port 8004 is occupied")
    schema = "native_m6_" + uuid4().hex[:12]
    engine, metadata = database(os.environ[args.database_url_env], schema)
    migrate(engine, metadata)
    redis = Redis.from_url(os.environ[args.redis_url_env], decode_responses=True)
    assert redis.ping()
    # A random namespace also prefixes every Celery broker key.
    env = {
        **os.environ,
        "MATHS_DATABASE_URL": os.environ[args.database_url_env],
        "MATHS_REDIS_URL": os.environ[args.redis_url_env],
        "MATHS_NAMESPACE": schema,
        "MATHS_QDRANT_URL": "http://127.0.0.1:6333",
        "MATHS_RUNTIME": "fake",
        "MATHS_RAG_ENABLED": "false",
    }
    artifacts = Path("sample_outputs/platform_m6")
    artifacts.mkdir(parents=True, exist_ok=True)
    processes, files = [], []

    def worker(group, concurrency):
        log = (artifacts / f"{schema}-{group}.log").open("wb")
        files.append(log)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "celery",
                "-A",
                "scripts.platform_m6_native_fixture:celery_app",
                "worker",
                "--pool=threads",
                "--concurrency",
                str(concurrency),
                "-Q",
                group,
                "--loglevel=WARNING",
                "--hostname",
                group + "@native",
            ],
            env={**env, "MATHS_WORKER_GROUP": group},
            stdout=log,
            stderr=log,
        )
        processes.append(process)
        return process

    try:
        normal = worker("reasoning", 8)
        worker("recovery", 1)
        log = (artifacts / f"{schema}-api.log").open("wb")
        files.append(log)
        processes.append(
            subprocess.Popen(
                [sys.executable, "-m", "scripts.platform_m6_native_fixture"],
                env=env,
                stdout=log,
                stderr=log,
            )
        )
        with httpx.Client(base_url="http://127.0.0.1:8004", timeout=10) as client:
            until = time.monotonic() + 45
            while True:
                try:
                    ready = client.get("/health/ready")
                    if ready.status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < until, "native fixture failed readiness"
                assert all(process.poll() is None for process in processes), (
                    "fixture process exited"
                )
                time.sleep(0.1)
            subprocess.run(
                [
                    sys.executable,
                    "scripts/smoke_platform_m6.py",
                    "--url",
                    "http://127.0.0.1:8004",
                    "--output",
                    str(artifacts / f"{schema}-load.json"),
                ],
                check=True,
                timeout=45,
            )
            session = client.post("/v1/sessions", json={}).json()["id"]
            response = client.post(
                f"/v1/sessions/{session}/tasks", json={"problem": "Native crash fixture."}
            )
            response.raise_for_status()
            task = response.json()
            until = time.monotonic() + 10
            while True:
                trace_response = client.get(task["trace_url"])
                trace_response.raise_for_status()
                trace = trace_response.json()["events"]
                if any(
                    e["event_type"] == "stage.completed" and e["stage_id"] == "retrieve"
                    for e in trace
                ):
                    break
                assert time.monotonic() < until
                time.sleep(0.1)
            crashed_at = time.monotonic()
            normal.kill()
            normal.wait(5)
            # Reserved recovery worker must finish even while normal worker is offline.
            until = crashed_at + 30
            while client.get(task["status_url"]).json()["status"] != "succeeded":
                assert time.monotonic() < until, "recovery exceeded 30 seconds"
                time.sleep(0.1)
            recovered_in = time.monotonic() - crashed_at
            trace = client.get(task["trace_url"]).json()["events"]
            assert any(e["event_type"] == "task.resumed" for e in trace)
            assert (
                sum(
                    e["event_type"] == "stage.completed" and e["stage_id"] == "retrieve"
                    for e in trace
                )
                == 1
            )
            print(
                json.dumps(
                    {
                        "native_transport": "passed",
                        "worker_crash_recovery_seconds": recovered_in,
                        "completed_retrieve_replays": 0,
                        "boundary": "PG + Redis + Celery; embedded Qdrant; Fake reasoning; not Docker",
                    }
                )
            )
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                process.wait(10)
        for file in files:
            file.close()
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()
        keys = list(redis.scan_iter(match=schema + ":*"))
        if keys:
            redis.delete(*keys)
        redis.close()


if __name__ == "__main__":
    main()
