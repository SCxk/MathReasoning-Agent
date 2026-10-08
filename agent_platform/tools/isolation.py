import asyncio
import json
import os
import sys


def windows_job(pid, *, memory_mb=256, cpu_seconds=5):
    import win32api
    import win32con
    import win32job

    job = win32job.CreateJobObject(None, "")
    try:
        limits = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
        limits["BasicLimitInformation"]["LimitFlags"] = (
            win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | win32job.JOB_OBJECT_LIMIT_PROCESS_TIME)
        limits["BasicLimitInformation"]["PerProcessUserTimeLimit"] = cpu_seconds * 10000000
        limits["ProcessMemoryLimit"] = memory_mb * 1024 * 1024
        win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, limits)
        process = win32api.OpenProcess(win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE, False, pid)
        try:
            win32job.AssignProcessToJobObject(job, process)
        finally:
            process.Close()
        return job
    except BaseException:
        job.Close()
        raise


async def isolated_calculate(arguments):
    # Do not forward application secrets to computation workers.
    allowed_env = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed_env}
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "agent_platform.tools.worker", env=env,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        creationflags=0x08000000 if os.name == "nt" else 0,
    )
    job = None
    try:
        if os.name == "nt":
            try:
                job = windows_job(process.pid)
            except Exception:
                return {"status": "failed", "error_code": "policy_rejected"}
        try:
            output, _ = await asyncio.wait_for(process.communicate(
                (json.dumps(arguments, allow_nan=False) + "\n").encode()), 5)
        except TimeoutError:
            return {"status": "failed", "error_code": "timeout", "retryable": False}
        if process.returncode != 0:
            return {"status": "failed", "error_code": "execution_error"}
        if len(output) > 65536:
            return {"status": "failed", "error_code": "invalid_result"}
        return json.loads(output)
    finally:
        if job is not None:
            job.Close()  # Kill the complete job tree, including on cancellation.
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        await process.wait()
