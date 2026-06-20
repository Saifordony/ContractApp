"""Tests for lexical retrieval and budget-aware selection."""
from __future__ import annotations

from backend.services.chunking import Chunk, chunk_text
from backend.services.retrieval import render_context, score_chunks, select_budgeted


def _chunks():
    text = (
        "Termination. Either party may terminate on thirty days notice.\n\n"
        "Payment. Fees are due within thirty days of invoice.\n\n"
        "Confidentiality. Information stays secret for three years."
    )
    return chunk_text(text, target_tokens=20)


def test_score_chunks_ranks_relevant_first():
    chunks = _chunks()
    scored = score_chunks("how do I terminate the agreement", chunks)
    assert scored
    top_chunk = scored[0][0]
    assert "terminate" in top_chunk.text.lower()


def test_score_chunks_empty():
    assert score_chunks("anything", []) == []


def test_select_budgeted_respects_budget():
    chunks = [Chunk(i, "word " * 50, i * 200, i * 200 + 200) for i in range(5)]
    scored = [(c, 1.0 - i * 0.1) for i, c in enumerate(chunks)]
    selected = select_budgeted(scored, token_budget=60)  # ~50 tokens per chunk
    assert 1 <= len(selected) <= 2
    # Returned in document order.
    assert selected == sorted(selected, key=lambda c: c.start)


def test_select_budgeted_always_returns_one():
    big = Chunk(0, "word " * 1000, 0, 5000)
    selected = select_budgeted([(big, 0.9)], token_budget=10)
    assert len(selected) == 1


def test_render_context_includes_markers():
    chunks = _chunks()
    rendered = render_context(chunks[:1])
    assert "[chunk" in rendered
