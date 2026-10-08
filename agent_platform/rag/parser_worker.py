import json
import os
from pathlib import Path
import sys

from agent_platform.tools.worker import deny_external_io


def main():
    request = json.loads(sys.stdin.buffer.readline(8192))
    if os.name != "nt":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    sys.addaudithook(deny_external_io)
    path = Path(request["path"]).resolve()
    def read_only(event, args):
        if event == "open":
            mode, flags = args[1:3]
            if (isinstance(mode, str) and any(char in mode for char in "wax+")) or (
                    isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)):
                raise PermissionError("parser_read_only")
    sys.addaudithook(read_only)
    from agent_platform.rag.parser import ParseRejected, parse_document
    try:
        parser = parse_document
        if request.get("questions"):
            from agent_platform.questions_parser import parse_questions
            parser = parse_questions
        result = {"status": "succeeded", "value": parser(path, request["media_type"]).model_dump()}
    except ParseRejected as exc:
        result = {"status": "failed", "error_code": str(exc)}
    except Exception:
        result = {"status": "failed", "error_code": "parse_failed"}
    sys.stdout.write(json.dumps(result, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":  # pragma: no cover - actual subprocess integration.
    main()
