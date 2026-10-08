"""Windows-native transport fixture: real PG/Redis/Celery, embedded Qdrant, Fake reasoning.

This deliberately does not validate Docker or remote Qdrant availability.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qdrant_client import QdrantClient
import agent_platform.deployment as bootstrap


class NativeFixture(bootstrap.Deployment):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.runtime.name != "fake" or self.documents is not None:
            raise ValueError("native_fixture_requires_fake_without_documents")
        self.qdrant.close()
        self.qdrant = QdrantClient(location=":memory:")


bootstrap.Deployment = NativeFixture

from agent_platform.celery_worker import celery_app as celery_app  # noqa: E402


def main():
    import uvicorn

    uvicorn.run(bootstrap.application(), host="127.0.0.1", port=8004, access_log=False)


if __name__ == "__main__":
    main()
