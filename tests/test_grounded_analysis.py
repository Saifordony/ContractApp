"""Unit tests for the unified grounded-analysis service."""

import json

from backend.services.grounded_analysis import ANALYSIS_SECTIONS, run_grounded_analysis

CONTRACT = (
    "SERVICE AGREEMENT. 1. Payment Terms. The Client shall pay all invoices within "
    "thirty (30) days of receipt. 2. Termination. Either party may terminate this "
    "agreement upon sixty (60) days written notice. 3. Confidentiality. Each party "
    "shall keep confidential information secret for a period of three years. 4. "
    "Governing Law. This agreement is governed by the laws of the State of New York."
)


def test_degraded_mode_when_no_llm_callable():
    result = run_grounded_analysis(CONTRACT, llm_callable=None)
    assert result["degraded_mode"] is True
    assert result["evaluation_source"] == "rule_based_fallback"
    # Every canonical section is present, each carrying its own confidence.
    assert set(result["sections"].keys()) == set(ANALYSIS_SECTIONS.keys())
    for section in result["sections"].values():
        assert "confidence" in section
        assert isinstance(section["evidence"], list)


def test_llm_mode_tags_source_and_uses_callable():
    calls = []

    def fake_llm(prompt: str) -> str:
        calls.append(prompt)
        return json.dumps(
            {
                "answer": "The contract requires payment within 30 days.",
                "confidence": 0.8,
                "evidence": [{"quote": "pay all invoices within thirty (30) days", "location": "Section 1"}],
                "risks": [],
                "missing_information": [],
            }
        )

    result = run_grounded_analysis(CONTRACT, llm_callable=fake_llm)
    assert result["degraded_mode"] is False
    assert result["evaluation_source"] == "llm"
    # The pipeline actually invoked the model (regression guard: every prior caller
    # ran the pipeline with no llm_callable, so the model was never called).
    assert calls, "expected the grounded pipeline to invoke the LLM callable"


def test_empty_text_rejected():
    try:
        run_grounded_analysis("   ")
    except ValueError:
        return
    raise AssertionError("expected ValueError for empty contract text")
