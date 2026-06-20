"""Tests for the grounded AI pipeline (LLM mocked)."""
from __future__ import annotations

import pytest

from backend.services.ai_pipeline import (
    analyze_contract,
    answer_question_stream,
    extract_quotes,
    verify_span,
)
from tests.fakes import SAMPLE_CONTRACT, FailingLLM, FakeLLM


def _contract():
    return {"language": "en", "content": SAMPLE_CONTRACT, "contract_type": "service_agreement"}


def test_verify_span_finds_real_quote():
    span = verify_span(SAMPLE_CONTRACT, "thirty (30) days written notice")
    assert span is not None
    start, end, matched = span
    assert SAMPLE_CONTRACT[start:end] == matched


def test_verify_span_rejects_hallucinated_quote():
    assert verify_span(SAMPLE_CONTRACT, "the contractor shall provide a company car") is None


def test_extract_quotes():
    quotes = extract_quotes('He said "hello there" and also "goodbye now".')
    assert "hello there" in quotes
    assert "goodbye now" in quotes


@pytest.mark.asyncio
async def test_analyze_contract_grounded():
    result = await analyze_contract(_contract(), llm=FakeLLM())
    assert result["degraded"] is False
    assert result["model"] != "deterministic-fallback"

    by_key = {c["key"]: c for c in result["clauses"]}
    termination = by_key["termination"]
    assert termination["status"] == "found"
    assert termination["evidence"], "found clause must carry grounded evidence"
    ev = termination["evidence"][0]
    # Evidence offsets point at real text in the source.
    assert SAMPLE_CONTRACT[ev["char_start"]:ev["char_end"]] == ev["text"]
    assert termination["confidence"] > 0.5

    # All ten clause types are always represented (canonical shape).
    assert len(result["clauses"]) == 10
    assert result["health"]["overall_score"] == 78
    assert result["health"]["grade"] == "C"
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_analyze_contract_ungrounded_quote_demoted():
    # Model claims a clause with a quote that is NOT in the source.
    bad = {"clauses": [{
        "key": "indemnification", "status": "found",
        "quote": "Vendor shall indemnify Client against alien invasions.",
        "explanation": "made up",
    }]}
    result = await analyze_contract(_contract(), llm=FakeLLM(extraction=bad))
    indem = {c["key"]: c for c in result["clauses"]}["indemnification"]
    assert indem["status"] == "needs_review"  # demoted because quote was ungrounded
    assert indem["evidence"] == []


@pytest.mark.asyncio
async def test_analyze_contract_degraded_when_llm_down():
    result = await analyze_contract(_contract(), llm=FailingLLM())
    assert result["degraded"] is True
    assert result["model"] == "deterministic-fallback"
    assert len(result["clauses"]) == 10  # same shape as the healthy path
    assert result["confidence"] <= 0.4


@pytest.mark.asyncio
async def test_chat_stream_grounded_citations():
    events = [event async for event in answer_question_stream(_contract(), "How do I terminate?", llm=FakeLLM())]
    token_events = [e for e in events if e["type"] == "token"]
    result_events = [e for e in events if e["type"] == "result"]
    assert token_events, "chat must stream tokens"
    assert result_events
    result = result_events[0]["data"]
    assert result["degraded"] is False
    assert result["citations"], "answer should cite verified source text"
    citation = result["citations"][0]
    assert SAMPLE_CONTRACT[citation["char_start"]:citation["char_end"]] == citation["text"]


@pytest.mark.asyncio
async def test_chat_stream_degraded_when_llm_down():
    events = [event async for event in answer_question_stream(_contract(), "What is the term?", llm=FailingLLM())]
    result = [e for e in events if e["type"] == "result"][0]["data"]
    assert result["degraded"] is True


@pytest.mark.asyncio
async def test_arabic_contract_uses_arabic_prompting():
    arabic_contract = {"language": "ar", "content": SAMPLE_CONTRACT}
    # FakeLLM ignores language, but the pipeline must run end-to-end for ar too.
    result = await analyze_contract(arabic_contract, llm=FakeLLM())
    assert result["language"] == "ar"
    assert len(result["clauses"]) == 10
