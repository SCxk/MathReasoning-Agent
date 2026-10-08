#!/usr/bin/env python3
"""Build Chinese LaTeX reading drafts from extracted PDF text using Argos Translate.

This is a pragmatic batch helper for large paper batches: it keeps page-level
alignment, escapes LaTeX-sensitive characters, and emits a XeLaTeX/ctex project.
It is intentionally conservative about source PDF layout; use the full
pdf-to-chinese-latex workflow for papers that need figure/table fidelity.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

import argostranslate.translate as argos_translate


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def get_translation(provider: str):
    if provider == "mymemory":
        return MyMemoryTranslator()
    langs = argos_translate.get_installed_languages()
    by_code = {lang.code: lang for lang in langs}
    if "en" not in by_code or "zh" not in by_code:
        raise SystemExit("Argos English->Chinese package is not installed.")
    return by_code["en"].get_translation(by_code["zh"])


class MyMemoryTranslator:
    def __init__(self, sleep_seconds: float = 1.2):
        self.sleep_seconds = sleep_seconds

    def translate(self, text: str) -> str:
        query = urllib.parse.quote(text[:4500])
        url = (
            "https://api.mymemory.translated.net/get"
            f"?q={query}&langpair=en%7Czh-CN"
        )
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=20) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                translated = data.get("responseData", {}).get("translatedText", "")
                if translated:
                    time.sleep(self.sleep_seconds)
                    return translated
            except Exception as exc:
                last_error = exc
                time.sleep(1.5 * (attempt + 1))
        if last_error:
            raise last_error
        raise RuntimeError("empty translation response")


def split_pages(raw_text: str) -> list[tuple[int, str]]:
    parts = re.split(r"^=+ PAGE (\d+) =+=\s*$", raw_text, flags=re.MULTILINE)
    pages: list[tuple[int, str]] = []
    for i in range(1, len(parts), 2):
        pages.append((int(parts[i]), parts[i + 1].strip()))
    if not pages and raw_text.strip():
        pages.append((1, raw_text.strip()))
    return pages


def paragraph_chunks(text: str, max_chars: int = 700) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for para in paras:
        if size + len(para) > max_chars and buf:
            chunks.append("\n\n".join(buf))
            buf = []
            size = 0
        if len(para) > max_chars:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sent in sentences:
                if size + len(sent) > max_chars and buf:
                    chunks.append("\n\n".join(buf))
                    buf = []
                    size = 0
                buf.append(sent)
                size += len(sent)
        else:
            buf.append(para)
            size += len(para)
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def translate_text(text: str, translator) -> str:
    out: list[str] = []
    for chunk in paragraph_chunks(text):
        try:
            out.append(translator.translate(chunk))
        except Exception as exc:
            out.append(f"[TRANSLATION ERROR: {exc}]\n{chunk}")
    return "\n\n".join(out)


def pdf_title(pdf: Path) -> str:
    try:
        proc = subprocess.run(
            ["pdfinfo", str(pdf)],
            check=False,
            text=True,
            capture_output=True,
        )
        for line in proc.stdout.splitlines():
            if line.startswith("Title:"):
                title = line.split(":", 1)[1].strip()
                if title:
                    return title
    except Exception:
        pass
    return pdf.stem


def translate_page(page_no: int, page_text: str, cache_dir: Path, translator) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"page_{page_no:03d}.txt"
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_text(encoding="utf-8", errors="replace")
    print(f"  page {page_no}", flush=True)
    zh = translate_text(page_text, translator)
    cache_path.write_text(zh, encoding="utf-8")
    return zh


def write_project(pdf: Path, out_dir: Path, translator) -> None:
    raw_path = out_dir / "raw.txt"
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)
    translated_dir = out_dir / "translated"
    translated_dir.mkdir(parents=True, exist_ok=True)

    raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
    pages = split_pages(raw_text)
    title = pdf_title(pdf)

    cache_dir = out_dir / "translated_pages"
    body_lines: list[str] = []
    for page_no, page_text in pages:
        zh = translate_page(page_no, page_text, cache_dir, translator)
        body_lines.append(rf"\section*{{第 {page_no} 页}}")
        for para in [p.strip() for p in zh.split("\n\n") if p.strip()]:
            body_lines.append(latex_escape(para))
            body_lines.append("")

    tex = rf"""% !TEX program = xelatex
\documentclass[UTF8,zihao=-4]{{ctexart}}
\usepackage[a4paper,margin=2.2cm]{{geometry}}
\usepackage{{hyperref}}
\usepackage{{longtable}}
\usepackage{{booktabs}}
\usepackage{{enumitem}}
\hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}
\title{{{latex_escape(title)}\\中文初译阅读稿}}
\author{{由 pdf-to-chinese-latex 批处理生成}}
\date{{}}
\begin{{document}}
\maketitle

\noindent\textbf{{说明：}}本文件由 PDF 文本抽取结果经离线英中翻译生成，按原 PDF 页码保持对齐，适合作为快速中文阅读稿。公式、图表和复杂排版请以原 PDF 或后续精修版为准。

{chr(10).join(body_lines)}
\end{{document}}
"""
    (translated_dir / "main.tex").write_text(tex, encoding="utf-8")
    readme = f"""# {title} 中文初译阅读稿

- Source PDF: `{pdf}`
- Raw text: `../raw.txt`
- Main file: `main.tex`
- Compiler: XeLaTeX

This is a page-aligned Chinese reading draft generated from extracted PDF text.
"""
    (translated_dir / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--provider", choices=["argos", "mymemory"], default="argos")
    parser.add_argument("--only-missing", action="store_true")
    args = parser.parse_args()

    translator = get_translation(args.provider)
    for pdf in sorted(args.pdf_dir.glob("*.pdf")):
        out_dir = args.out_root / f"{pdf.stem}_中文版"
        if args.only_missing:
            cache_dir = out_dir / "translated_pages"
            has_missing = False
            for page in cache_dir.glob("page_*.txt"):
                s = page.read_text(encoding="utf-8", errors="replace")
                if (
                    "TRANSLATION ERROR" in s
                    or "Too Many Requests" in s
                    or "UNEXPECTED_EOF" in s
                ):
                    page.unlink()
                    has_missing = True
            if not has_missing:
                continue
        print(f"[translate] {pdf.name}")
        write_project(pdf, out_dir, translator)


if __name__ == "__main__":
    main()
