"""Serve the optional locally built chat UI without exposing source or private files."""

from pathlib import Path

from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


CHAT_DIRECTORY = Path(__file__).parent / "static" / "chat"


def install_chat(app, directory: Path | None = None):
    root = directory if directory is not None else CHAT_DIRECTORY

    @app.get("/chat", include_in_schema=False)
    @app.get("/chat/", include_in_schema=False)
    async def chat():
        index = root / "index.html"
        if not index.is_file():
            return JSONResponse({"error": {"code": "chat_not_built"}}, 503)
        return FileResponse(index, headers={"Cache-Control": "no-store"})

    if (root / "assets").is_dir():
        app.mount("/chat/assets", StaticFiles(directory=root / "assets"), name="chat_assets")
    else:
        @app.get("/chat/assets/{asset_path:path}", include_in_schema=False)
        async def missing_asset(asset_path: str):
            return JSONResponse({"error": {"code": "not_found"}}, 404)
