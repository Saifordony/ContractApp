import pytest

pytest.importorskip("reportlab")

from frontend.services.reporting import build_professional_report_pdf, simplify_text


REPORT_PAYLOAD = {
    "health_evaluation": {
        "health_score": 68,
        "risk_level": "medium",
        "contract_type": "employment",
        "reasoning": "This contract is usable, but several points should be clarified before approval.",
        "missing_critical_clauses": ["governing_law"],
        "required_changes": ["Add the law that applies and clarify leave entitlement."],
        "issues": ["Leave policy is missing.", "Governing law is not clear."],
        "dimensions": [
            {
                "name": "Risk Exposure",
                "score": 60,
                "reason": "Some risk terms are unclear.",
                "recommended_action": "Clarify responsibility for losses.",
                "supporting_evidence": [{"quote": "Either party may terminate with 30 days notice."}],
            },
            {
                "name": "Commercial Clarity",
                "score": 75,
                "reason": "Payment timing is clear.",
                "recommended_action": "Confirm payment currency and deductions.",
            },
        ],
    },
    "structured_clauses": {
        "clauses": {
            "termination": {
                "status": "found",
                "confidence": 0.86,
                "extracted_text": "Either party may terminate this Agreement by giving 30 days written notice.",
                "evidence_snippets": [{"quote": "Either party may terminate this Agreement by giving 30 days written notice.", "location": "section:Termination"}],
                "recommended_action": "Confirm whether immediate termination rights are needed.",
            },
            "leave_policy": {
                "status": "not_found",
                "confidence": 0.0,
                "extracted_text": None,
                "evidence_snippets": [],
                "recommended_action": "Add annual leave, sick leave, and public holiday rules.",
            },
        }
    },
    "benchmark_result": {
        "benchmark_context": {
            "benchmark_basis": "Rule-based employment contract standard",
            "sample_size": None,
        },
        "overall_position": {"alignment_score": 61, "position_label": "Partially Aligned"},
        "your_contract_vs_benchmark": [
            {
                "review_area": "Termination",
                "your_contract": "30 days written notice.",
                "result": "Aligned",
                "recommendation": "Keep the notice period clear.",
            },
            {
                "review_area": "Leave Policy",
                "your_contract": "Not found",
                "result": "Not found",
                "recommendation": "Add leave policy wording.",
            },
        ],
    },
}


def _pdf_text(pdf_bytes: bytes) -> str:
    # ReportLab compression is disabled in the report generator so tests can
    # assert visible labels without requiring PDF parsing dependencies.
    return pdf_bytes.decode("latin-1", errors="ignore")


def test_professional_pdf_generates_with_cover_and_core_sections():
    pdf = build_professional_report_pdf("Employment Agreement", REPORT_PAYLOAD, client_name="Alpha LLC")
    assert pdf.startswith(b"%PDF")
    text = _pdf_text(pdf)
    assert "Contract Intelligence" in text
    assert "Contract Review Report" in text
    assert "Alpha LLC" in text
    assert "Employment Agreement" in text
    assert "Executive Summary" in text
    assert "Contract Health" in text
    assert "Benchmark Comparison" in text
    assert "Key Extracted Terms" in text
    assert "Appendix: Evidence Snippets" in text


def test_professional_pdf_includes_chart_labels_and_extracted_evidence():
    text = _pdf_text(build_professional_report_pdf("Employment Agreement", REPORT_PAYLOAD, client_name="Alpha LLC"))
    assert "Chart: Contract Health score by dimension" in text
    assert "Chart: Benchmark alignment by clause type" in text
    assert "Chart: Risk severity breakdown" in text
    assert "Chart: Confidence levels by section" in text
    assert "Chart: Extracted clauses completeness" in text
    assert "Either party may terminate" in text
    assert "Leave Policy" in text


def test_professional_pdf_handles_missing_ai_data_and_long_text():
    long_text = "Payment must be made within 30 days. " * 120
    payload = {"clauses": {"payment_terms": long_text}, "health_evaluation": {"health_score": 0, "risk_level": "high"}}
    pdf = build_professional_report_pdf("Long Contract", payload, client_name="No Benchmark Client")
    text = _pdf_text(pdf)
    assert "Long Contract" in text
    assert "Benchmark data was not available" in text
    assert "Payment Terms" in text


def test_simplify_text_replaces_hard_legal_jargon():
    assert "one-sided risk" in simplify_text("The indemnification provision creates asymmetric exposure.").lower()
