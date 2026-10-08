"""Trusted one-shot computation worker; stdin is data, never source code."""

import json
import os
import sys


def deny_external_io(event, args):
    if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"}:
        raise PermissionError("worker_external_io_denied")


def main():
    # Parent attaches the Windows Job before releasing this stdin gate.
    request = json.loads(sys.stdin.buffer.readline(70000))
    if os.name != "nt":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    sys.addaudithook(deny_external_io)
    from agent_platform.tools.symbolic import PolicyRejected, calculate
    from agent_platform.tools.schemas import CalculateArguments
    try:
        args = CalculateArguments.model_validate(request).model_dump()
        result = {"status": "succeeded", "value": calculate(args)}
    except PolicyRejected:
        result = {"status": "failed", "error_code": "policy_rejected"}
    except Exception:
        result = {"status": "failed", "error_code": "execution_error"}
    sys.stdout.write(json.dumps(result, allow_nan=False))


if __name__ == "__main__":  # pragma: no cover - exercised by isolated-process integration.
    main()
