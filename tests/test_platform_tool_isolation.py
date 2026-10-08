import asyncio
import io
import json
import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agent_platform.tools import isolation, worker
from agent_platform.tools.symbolic import PolicyRejected, calculate


def args():
    return {"expression": "1+1", "operation": "simplify", "variables": [], "assumptions": []}


@pytest.mark.parametrize("scenario,code", [
    ("job_error", "policy_rejected"), ("timeout", "timeout"), ("returncode", "execution_error"),
    ("oversized", "invalid_result"), ("kill_race", "timeout"), ("success", None),
])
def test_isolated_process_failures_cleanup_and_do_not_inherit_secrets(scenario, code):
    process = Mock(pid=123, returncode=None)
    job = Mock()
    async def communicate(data):
        if scenario in {"timeout", "kill_race"}:
            raise TimeoutError
        process.returncode = 1 if scenario == "returncode" else 0
        return (b"x" * 65537 if scenario == "oversized" else b'{"status":"succeeded","value":{}}'), b""
    async def wait():
        process.returncode = process.returncode if process.returncode is not None else -9
    process.communicate, process.wait = communicate, wait
    if scenario == "kill_race":
        process.kill.side_effect = ProcessLookupError
    launch = AsyncMock(return_value=process)
    with patch.object(isolation.asyncio, "create_subprocess_exec", launch), \
         patch.object(isolation, "windows_job", side_effect=RuntimeError() if scenario == "job_error" else None,
                      return_value=job), \
         patch.object(isolation, "os", SimpleNamespace(name="nt", environ={"SYSTEMROOT": "Windows", "INTERN_API_KEY": "not_forwarded"})):
        result = asyncio.run(isolation.isolated_calculate(args()))
    assert result.get("error_code") == code
    assert "INTERN_API_KEY" not in launch.call_args.kwargs["env"]
    if scenario != "job_error":
        job.Close.assert_called_once()
    if scenario in {"timeout", "kill_race", "job_error"}:
        process.kill.assert_called_once()


def test_isolated_task_cancellation_kills_worker_and_reaps_it():
    async def run():
        started = asyncio.Event()
        process = Mock(pid=123, returncode=None)
        async def communicate(data):
            started.set()
            await asyncio.Event().wait()
        process.communicate = communicate
        process.wait = AsyncMock()
        with patch.object(isolation.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)), \
             patch.object(isolation, "os", SimpleNamespace(name="posix", environ={})):
            work = asyncio.create_task(isolation.isolated_calculate(args()))
            await started.wait()
            work.cancel()
            with pytest.raises(asyncio.CancelledError):
                await work
        process.kill.assert_called_once()
        process.wait.assert_awaited_once()
    asyncio.run(run())


@pytest.mark.skipif(os.name != "nt", reason="Windows Job error path")
def test_windows_job_assignment_error_closes_handles():
    import win32job
    from agent_platform.tools.isolation import windows_job
    process = subprocess.Popen([sys.executable, "-c", "import sys;sys.stdin.readline()"], stdin=subprocess.PIPE)
    try:
        with patch.object(win32job, "AssignProcessToJobObject", side_effect=RuntimeError("denied")):
            with pytest.raises(RuntimeError):
                windows_job(process.pid)
    finally:
        process.kill()
        process.wait()
        process.stdin.close()


@pytest.mark.parametrize("event", ["socket.__new__", "socket.connect", "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn"])
def test_worker_audit_policy_denies_network_and_child_execution(event):
    with pytest.raises(PermissionError):
        worker.deny_external_io(event, ())
    worker.deny_external_io("import", ())


def test_actual_subprocess_audit_hook_denies_socket_creation():
    result = subprocess.run([sys.executable, "-c", "import sys,socket; from agent_platform.tools.worker import deny_external_io; sys.addaudithook(deny_external_io); socket.socket()"],
                            capture_output=True, timeout=5)
    assert result.returncode != 0 and b"worker_external_io_denied" in result.stderr


@pytest.mark.parametrize("scenario", ["success", "policy", "error"])
def test_worker_protocol_and_posix_limits_without_altering_test_process(scenario):
    stdout = io.StringIO()
    stdin = SimpleNamespace(buffer=io.BytesIO(json.dumps(args()).encode() + b"\n"))
    resource = Mock(RLIMIT_AS=9, RLIMIT_CPU=0)
    calculate_mock = Mock(return_value={"value": "2"})
    if scenario == "policy":
        calculate_mock.side_effect = PolicyRejected()
    elif scenario == "error":
        calculate_mock.side_effect = ArithmeticError()
    with patch.object(worker.sys, "stdin", stdin), patch.object(worker.sys, "stdout", stdout), \
         patch.object(worker.sys, "addaudithook", Mock()), \
         patch.object(worker, "os", SimpleNamespace(name="posix")), \
         patch.dict(sys.modules, {"resource": resource}), \
         patch("agent_platform.tools.symbolic.calculate", calculate_mock):
        worker.main()
    assert resource.setrlimit.call_count == 2
    data = json.loads(stdout.getvalue())
    assert data["status"] == ("succeeded" if scenario == "success" else "failed")


def test_symbolic_result_limit_and_nonreal_exponent():
    with pytest.raises(PolicyRejected):
        calculate({**args(), "expression": "x**sqrt(-1)", "variables": ["x"]})
    # Oversized output is bounded even when generated by the fixed operation.
    import sympy
    with patch.object(sympy, "simplify", return_value="x" * 8001):
        with pytest.raises(PolicyRejected):
            calculate(args())


def test_worker_windows_protocol_branch_and_validation_failure():
    stdout = io.StringIO()
    with patch.object(worker.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b'{}\n'))), \
         patch.object(worker.sys, "stdout", stdout), patch.object(worker.sys, "addaudithook", Mock()), \
         patch.object(worker, "os", SimpleNamespace(name="nt")):
        worker.main()
    assert json.loads(stdout.getvalue())["error_code"] == "execution_error"


@pytest.mark.skipif(os.name != "nt", reason="Windows memory enforcement")
def test_actual_memory_allocation_exceeding_job_limit_is_rejected():
    process = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.readline();\ntry: bytearray(300*1024*1024)\nexcept MemoryError: print('memory_limit_enforced')"],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    job = isolation.windows_job(process.pid)
    try:
        output, _ = process.communicate(b"go\n", timeout=5)
        assert output.strip() == b"memory_limit_enforced"
    finally:
        job.Close()
        process.wait()
