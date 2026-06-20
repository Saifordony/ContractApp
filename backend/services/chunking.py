"""Sentence-aware chunking with real sentence-level overlap.

Chunks never sever a sentence: text is split on sentence punctuation (EN + AR) and
paragraph breaks, offsets into the original document are preserved, and consecutive
chunks overlap by whole sentences so a clause spanning a boundary stays intact.
"""
from __future__ import annotations

from dataclasses import dataclass


def estimate_tokens(text: str) -> int:
    """Cheap, model-agnostic token estimate (~4 chars/token)."""
    return max(1, len(text) // 4)


@dataclass
class Sentence:
    start: int
    end: int
    text: str


@dataclass
class Chunk:
    id: int
    text: str
    start: int
    end: int


_SENTENCE_ENDERS = ".!?؟۔"
_TRAILING = "\"'’”)]»"


def split_sentences(text: str) -> list[Sentence]:
    sentences: list[Sentence] = []
    n = len(text)
    start = 0
    i = 0
    while i < n:
        ch = text[i]
        boundary_end: int | None = None
        if ch in _SENTENCE_ENDERS:
            j = i + 1
            while j < n and text[j] in _SENTENCE_ENDERS + _TRAILING:
                j += 1
            if j >= n or text[j].isspace():
                boundary_end = j
        elif ch == "\n":
            j = i + 1
            while j < n and text[j] in " \t\r":
                j += 1
            if j < n and text[j] == "\n":  # blank line = paragraph break
                while j < n and text[j].isspace():
                    j += 1
                boundary_end = j
        if boundary_end is not None:
            segment = text[start:boundary_end]
            if segment.strip():
                sentences.append(Sentence(start, boundary_end, segment))
            start = boundary_end
            i = boundary_end
        else:
            i += 1
    if start < n and text[start:n].strip():
        sentences.append(Sentence(start, n, text[start:n]))
    return sentences


def chunk_text(text: str, *, target_tokens: int = 220, overlap_sentences: int = 1) -> list[Chunk]:
    sentences = split_sentences(text)
    if not sentences:
        cleaned = text.strip()
        return [Chunk(0, cleaned, 0, len(text))] if cleaned else []

    chunks: list[Chunk] = []
    current: list[Sentence] = []
    current_tokens = 0
    chunk_id = 0

    def flush() -> None:
        nonlocal chunk_id
        if not current:
            return
        start = current[0].start
        end = current[-1].end
        chunks.append(Chunk(chunk_id, text[start:end], start, end))
        chunk_id += 1

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence.text)
        if current and current_tokens + sentence_tokens > target_tokens:
            flush()
            current = current[-overlap_sentences:] if overlap_sentences > 0 else []
            current_tokens = sum(estimate_tokens(s.text) for s in current)
        current.append(sentence)
        current_tokens += sentence_tokens
    flush()
    return chunks
