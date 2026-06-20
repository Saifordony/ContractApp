"""Tests for the bilingual prompt builders."""
from __future__ import annotations

from backend.services.prompts import chat_messages, extraction_messages, health_messages


def _joined(messages) -> str:
    return " ".join(m["content"] for m in messages)


def test_extraction_lists_clause_keys_and_schema():
    text = _joined(extraction_messages("CTX", "en"))
    assert "termination" in text and "confidentiality" in text
    assert '"clauses"' in text
    assert "verbatim" in text.lower()


def test_extraction_arabic_directive():
    assert "Arabic" in _joined(extraction_messages("CTX", "ar"))


def test_extraction_includes_correction():
    text = _joined(extraction_messages("CTX", "en", correction="fix the quotes"))
    assert "fix the quotes" in text


def test_health_messages_define_dimensions():
    text = _joined(health_messages("CTX", "termination=found", "en"))
    assert '"dimensions"' in text and "clarity" in text


def test_chat_messages_demand_context_grounding():
    text = _joined(chat_messages("CTX", "What is the term?", "en"))
    assert "CONTEXT" in text
    assert "What is the term?" in text
    assert "double quotes" in text.lower()
