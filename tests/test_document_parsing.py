"""Tests for document parsing and language detection."""
from __future__ import annotations

import importlib

import pytest

from backend.services.document_parsing import (
    detect_language,
    parse_document,
    parse_text,
)


def test_parse_text_from_bytes():
    parsed = parse_text(b"  hello world  ")
    assert parsed.text == "hello world"
    assert parsed.source_format == "text"


def test_detect_language_english():
    assert detect_language("This is an English contract clause.") == "en"


def test_detect_language_arabic():
    assert detect_language("هذا عقد باللغة العربية بين الطرفين") == "ar"


def test_parse_document_dispatches_text():
    parsed = parse_document("notes.txt", b"plain content", "text/plain")
    assert parsed.source_format == "text"
    assert parsed.text == "plain content"


def test_parse_document_rejects_legacy_doc():
    with pytest.raises(ValueError):
        parse_document("old.doc", b"\x00\x01", None)


@pytest.mark.skipif(importlib.util.find_spec("docx") is None, reason="python-docx not installed")
def test_parse_docx_roundtrip():
    import io

    import docx

    document = docx.Document()
    document.add_paragraph("Termination clause text.")
    buffer = io.BytesIO()
    document.save(buffer)

    parsed = parse_document("c.docx", buffer.getvalue(), None)
    assert parsed.source_format == "docx"
    assert "Termination clause text." in parsed.text
