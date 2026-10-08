"""Bound multipart bytes before Starlette allocates/spools the uploaded file."""

from starlette.responses import JSONResponse
from starlette.formparsers import MultiPartException

from agent_platform.rag.models import MAX_BYTES


class UploadLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http" or scope["method"] != "POST"
                or not scope["path"].startswith("/v1/sessions/")
                or not scope["path"].endswith(("/documents", "/question-batches"))):
            return await self.app(scope, receive, send)
        maximum = MAX_BYTES + 65536
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await JSONResponse({"error": {"code": "invalid_request"}}, 400)(scope, receive, send)
        if declared < 0 or declared > maximum:
            return await JSONResponse({"error": {"code": "file_too_large"}}, 413)(scope, receive, send)
        count = 0
        async def bounded():
            nonlocal count
            message = await receive()
            count += len(message.get("body", b""))
            if count > maximum:
                raise MultiPartException("file_too_large")
            return message
        await self.app(scope, bounded, send)
