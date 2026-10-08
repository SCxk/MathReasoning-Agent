from typing import Literal

from pydantic import Field

from agent_platform.tools.schemas import DTO, UUIDText, Passage as Passage, SourceMetadata as SourceMetadata


PARSER_VERSION = "pypdf-6.1.1-md-math-v1"
CHUNKER_VERSION = "formula-blocks-v1-1200-2000"
SPARSE_VERSION = "unicode-bigram-latex-bm25l-v1"
RERANK_VERSION = "d6-v1-045-035-010-010-k60"
MAX_BYTES = 20 * 1024 * 1024
MAX_TEXT = 2_000_000
MAX_CHUNKS = 10000


class Document(DTO):
    id: UUIDText
    session_id: UUIDText
    original_name: str = Field(max_length=200)
    media_type: Literal["application/pdf", "text/markdown"]
    size_bytes: int = Field(ge=1, le=MAX_BYTES)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    storage_key: str
    status: Literal["indexing", "ready", "failed", "expired"] = "indexing"
    page_count: int | None = None
    chunk_count: int = 0
    parser_version: str | None = None
    index_version: str | None = None
    error_code: str | None = None
    domain: str | None = Field(default=None, max_length=100)
    problem_type: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=200)
    created_at: str
    expires_at: str

    def projection(self):
        result = self.model_dump(exclude={"storage_key"})
        result["status_url"] = f"/v1/sessions/{self.session_id}/documents/{self.id}"
        return result


class ParsedChunk(DTO):
    text: str = Field(min_length=1, max_length=2000)
    heading: str = Field(default="", max_length=300)
    page_start: int | None = None
    page_end: int | None = None


class ParsedDocument(DTO):
    page_count: int | None
    chunks: list[ParsedChunk] = Field(min_length=1, max_length=MAX_CHUNKS)
