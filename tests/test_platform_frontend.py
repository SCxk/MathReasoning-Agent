"""Frontend assets stay separate from API behavior."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_platform.frontend import install_chat


def test_chat_without_build_is_explicit_and_assets_are_not_server_errors(tmp_path):
    app = FastAPI()
    install_chat(app, tmp_path)
    with TestClient(app) as client:
        for path in ("/chat", "/chat/"):
            response = client.get(path)
            assert response.status_code == 503
            assert response.json() == {"error": {"code": "chat_not_built"}}
        assert client.get("/chat/assets/missing.js").status_code == 404


def test_chat_build_and_safe_static_asset_serving(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<title>MathReasoning-Agent</title>", encoding="utf8")
    (tmp_path / "assets" / "chat.js").write_text("export {}", encoding="utf8")
    private = tmp_path / "private.txt"
    private.write_text("private fixture", encoding="utf8")
    app = FastAPI()
    install_chat(app, tmp_path)
    with TestClient(app) as client:
        for path in ("/chat", "/chat/"):
            response = client.get(path)
            assert response.status_code == 200 and "MathReasoning-Agent" in response.text
            assert response.headers["cache-control"] == "no-store"
        assert client.get("/chat/assets/chat.js").status_code == 200
        assert client.get("/chat/assets/%2e%2e/private.txt").status_code == 404
        assert client.get("/chat/assets/missing.js").status_code == 404
        assert client.get("/chat/private.txt").status_code == 404


def test_container_build_includes_frontend_and_excludes_local_outputs():
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "Dockerfile").read_text()
    assert "COPY --from=frontend" in dockerfile
    assert "RUN npm ci" in dockerfile and "RUN npm run build" in dockerfile
    assert "!client/package-lock.json" in (root / ".dockerignore").read_text()
    assert "agent_platform/static/chat/" in (root / ".gitignore").read_text()
