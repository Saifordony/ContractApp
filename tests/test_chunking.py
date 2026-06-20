"""Tests for sentence-aware chunking."""
from __future__ import annotations

from backend.services.chunking import chunk_text, estimate_tokens, split_sentences


def test_split_sentences_preserves_offsets():
    text = "First sentence. Second sentence! Third?"
    sentences = split_sentences(text)
    assert len(sentences) == 3
    for sentence in sentences:
        assert text[sentence.start:sentence.end] == sentence.text


def test_split_sentences_handles_paragraph_breaks():
    text = "Clause one is here.\n\nClause two is separate."
    sentences = split_sentences(text)
    assert len(sentences) == 2


def test_chunk_text_never_severs_a_sentence():
    sentence = "This is one complete clause that must not be split mid sentence. "
    text = sentence * 40
    chunks = chunk_text(text, target_tokens=60, overlap_sentences=1)
    assert len(chunks) > 1
    for chunk in chunks:
        # Each chunk's text is an exact substring at its recorded offsets.
        assert text[chunk.start:chunk.end] == chunk.text
        # No chunk ends in the middle of a word from our repeated sentence.
        assert chunk.text.strip().endswith(".") or chunk.text.strip().endswith("sentence.")


def test_chunk_text_overlaps_sentences():
    text = "Alpha one. Bravo two. Charlie three. Delta four. Echo five. Foxtrot six."
    chunks = chunk_text(text, target_tokens=8, overlap_sentences=1)
    assert len(chunks) >= 2
    # Consecutive chunks share overlapping character ranges.
    assert chunks[1].start < chunks[0].end


def test_estimate_tokens_monotonic():
    assert estimate_tokens("a" * 4) <= estimate_tokens("a" * 40)


def test_chunk_empty_text():
    assert chunk_text("") == []
