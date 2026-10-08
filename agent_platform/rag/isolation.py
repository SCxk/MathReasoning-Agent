import asyncio
import json
import os
import sys

from agent_platform.rag.models import ParsedDocument
from agent_platform.tools.isolation import windows_job


class ParserFailure(ValueError):
    pass


async def isolated_parse(path, media_type, *, questions=False):
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG"}}
    process = await asyncio.create_subprocess_exec(sys.executable, "-B", "-m", "agent_platform.rag.parser_worker",
        env=env, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL, creationflags=0x08000000 if os.name == "nt" else 0)
    job = None
    try:
        if os.name == "nt":
            try:
                job = windows_job(process.pid, memory_mb=512, cpu_seconds=30)
            except Exception:
                raise ParserFailure("parser_isolation_unavailable") from None
        try:
            raw, _ = await asyncio.wait_for(process.communicate((json.dumps({
                "path": str(path.resolve()), "media_type": media_type, "questions": questions}) + "\n").encode()), 30)
        except TimeoutError:
            raise ParserFailure("parser_timeout") from None
        if process.returncode != 0 or len(raw) > 16 * 1024 * 1024:
            raise ParserFailure("parser_resource_limit")
        result = json.loads(raw)
        if result["status"] != "succeeded":
            raise ParserFailure(result["error_code"])
        if questions:
            from agent_platform.questions_parser import QuestionDocument
            return QuestionDocument.model_validate(result["value"])
        return ParsedDocument.model_validate(result["value"])
    finally:
        if job:
            job.Close()
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        await process.wait()
