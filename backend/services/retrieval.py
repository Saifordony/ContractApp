"""Deterministic, offline lexical retrieval with budget-aware selection.

No embedding service is required: chunks are scored against a query with
IDF-weighted cosine similarity (EN + AR tokens). Selection is token-budget-aware
and applied BEFORE the prompt is built — we pick fewer, more relevant chunks
rather than truncating a finished prompt.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from backend.services.chunking import Chunk, estimate_tokens

_TOKEN_RE = re.compile(r"[A-Za-z0-9؀-ۿݐ-ݿ]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def score_chunks(query: str, chunks: list[Chunk]) -> list[tuple[Chunk, float]]:
    """Return chunks scored by IDF-weighted cosine similarity, best first."""
    if not chunks:
        return []
    docs = [tokenize(c.text) for c in chunks]
    df: Counter = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1
    n = len(docs)
    idf = {term: math.log(1 + n / (1 + count)) for term, count in df.items()}

    q_counts = Counter(tokenize(query))
    q_norm = math.sqrt(sum((count * idf.get(term, 0.0)) ** 2 for term, count in q_counts.items())) or 1.0

    scored: list[tuple[Chunk, float]] = []
    for chunk, doc in zip(chunks, docs):
        d_counts = Counter(doc)
        numerator = sum(
            q_counts[term] * d_counts.get(term, 0) * (idf.get(term, 0.0) ** 2)
            for term in q_counts
        )
        d_norm = math.sqrt(sum((count * idf.get(term, 0.0)) ** 2 for term, count in d_counts.items())) or 1.0
        scored.append((chunk, numerator / (q_norm * d_norm)))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


def select_budgeted(scored: list[tuple[Chunk, float]], *, token_budget: int) -> list[Chunk]:
    """Greedily select the most relevant chunks that fit the token budget,
    then return them in document order for a coherent context window."""
    selected: list[Chunk] = []
    used = 0
    for chunk, score in scored:
        if score <= 0 and selected:
            break
        chunk_tokens = estimate_tokens(chunk.text)
        if used + chunk_tokens > token_budget:
            continue  # skip; a smaller relevant chunk may still fit
        selected.append(chunk)
        used += chunk_tokens
        if used >= token_budget:
            break
    if not selected and scored:
        selected = [scored[0][0]]  # always provide at least one chunk
    selected.sort(key=lambda c: c.start)
    return selected


def render_context(chunks: list[Chunk]) -> str:
    """Render selected chunks with stable markers the model can reference."""
    return "\n\n".join(f"[chunk {c.id}]\n{c.text.strip()}" for c in chunks)
