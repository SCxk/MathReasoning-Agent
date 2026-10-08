"""Heading, fence and display-math aware text blocks with page provenance."""

import re

from agent_platform.rag.models import MAX_TEXT, MAX_CHUNKS, ParsedChunk, ParsedDocument
from agent_platform.safety import sanitize_text


class ParseRejected(ValueError):
    pass


def evidence_text(text):
    text = sanitize_text(text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\[([^\]\n]*)\]\([^\n)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", "[link removed]", text)
    # Reference documents are not HTML; remove active markup rather than render it.
    spans = re.split(r"(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\$[^$\n]+\$|\\\([^\n]*?\\\))", text)
    text = "".join(piece if index % 2 else re.sub(
        r"</?[A-Za-z][A-Za-z0-9]*(?:\s+[^<>]*|\s*)/?>", "", piece)
        for index, piece in enumerate(spans))
    return text.strip()


def blocks(text):
    spans = re.split(r"(```[\s\S]*?```|~~~[\s\S]*?~~~|\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\])", text)
    for index, span in enumerate(spans):
        if index % 2:
            yield span, True
            continue
        if any(marker in span for marker in ("```", "~~~", "$$", r"\[")):
            raise ParseRejected("unclosed_formula_or_fence")
        pending = []
        for line in span.splitlines(keepends=True):
            if not line.strip() or re.match(r"^#{1,6}\s", line):
                if pending:
                    yield "".join(pending), False
                    pending = []
                if line.strip():
                    yield line, False
            else:
                pending.append(line)
        if pending:
            yield "".join(pending), False


def split_prose(text):
    # Inline formula/code spans are atomic too; do not split inside them.
    pieces = re.split(r"(\$[^$\n]+\$|\\\([^\n]*?\\\)|`[^`\n]*`)", text)
    for piece in pieces:
        if not piece:
            continue
        if piece.startswith(("$", r"\(", "`")):
            if len(piece) > 2000:
                raise ParseRejected("formula_too_large")
            yield piece
        else:
            for start in range(0, len(piece), 1000):
                yield piece[start:start + 1000]


def chunk_pages(pages, *, pdf=False):
    chunks, total = [], 0
    for page, text in enumerate(pages, 1):
        total += len(text)
        if total > MAX_TEXT:
            raise ParseRejected("text_limit")
        text = evidence_text(text)
        current, heading = "", ""
        def flush():
            nonlocal current
            if current.strip():
                chunks.append(ParsedChunk(text=current.strip(), heading=heading,
                    page_start=page if pdf else None, page_end=page if pdf else None))
            current = ""
        for block, protected in blocks(text):
            if re.match(r"^#{1,6}\s", block):
                flush()
                heading = block.strip().lstrip("#").strip()[:300]
            if protected and len(block) > 2000:
                raise ParseRejected("formula_too_large")
            units = [block] if protected else split_prose(block)
            for unit in units:
                if current and len(current) + len(unit) > 1200:
                    flush()
                current += unit
        flush()
        if len(chunks) > MAX_CHUNKS:
            raise ParseRejected("chunk_limit")
    if not chunks:
        raise ParseRejected("no_extractable_text")
    return ParsedDocument(page_count=len(pages) if pdf else None, chunks=chunks)


def parse_document(path, media_type):
    if media_type == "text/markdown":
        try:
            return chunk_pages([path.read_text(encoding="utf-8-sig")])
        except UnicodeError:
            raise ParseRejected("invalid_utf8") from None
    from pypdf import PdfReader
    reader = PdfReader(path, strict=True)
    if reader.is_encrypted:
        raise ParseRejected("encrypted_pdf")
    if len(reader.pages) > 500:
        raise ParseRejected("page_limit")
    pages, total = [], 0
    for page in reader.pages:
        text = page.extract_text() or ""
        total += len(text)
        if total > MAX_TEXT:
            raise ParseRejected("text_limit")
        pages.append(text)
    return chunk_pages(pages, pdf=True)
