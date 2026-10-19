"""Text cleaning and chunking for retrieval.

Chunks are heading-aware and overlap slightly so that facts split across
paragraph boundaries are still retrievable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

WHITESPACE_RE = re.compile(r"[ \t\u00a0]+")
BLANKLINE_RE = re.compile(r"\n{3,}")


@dataclass
class TextChunk:
    text: str
    heading: str | None = None
    index: int = 0


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = WHITESPACE_RE.sub(" ", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    return BLANKLINE_RE.sub("\n\n", text).strip()


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def chunk_text(
    text: str,
    *,
    max_chars: int = 1400,
    overlap_chars: int = 200,
) -> list[TextChunk]:
    """Split text into heading-aware chunks.

    A chunk never mixes unrelated headings when a heading-like line (short,
    title-ish) is detected.
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []

    blocks: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            blocks.append((current_heading, "\n".join(buffer).strip()))
            buffer.clear()

    for line in cleaned.split("\n"):
        if _looks_like_heading(line):
            flush()
            current_heading = line
            continue
        buffer.append(line)
    flush()

    chunks: list[TextChunk] = []
    for heading, body in blocks:
        if not body:
            if heading:
                chunks.append(TextChunk(text=heading, heading=heading))
            continue
        start = 0
        while start < len(body):
            end = min(start + max_chars, len(body))
            if end < len(body):
                window = body[start:end]
                cut = max(window.rfind("\n"), window.rfind(". "))
                if cut > max_chars * 0.5:
                    end = start + cut + 1
            piece = body[start:end].strip()
            if piece:
                chunks.append(TextChunk(text=piece, heading=heading))
            if end >= len(body):
                break
            start = max(end - overlap_chars, start + 1)

    for i, chunk in enumerate(chunks):
        chunk.index = i
    return chunks


def _looks_like_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 90:
        return False
    if line.endswith((":", "?")):
        return True
    words = line.split()
    if 1 <= len(words) <= 8 and (line.isupper() or line.istitle()):
        return True
    return False
