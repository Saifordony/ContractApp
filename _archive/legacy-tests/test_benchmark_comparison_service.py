import pytest

from backend.services.benchmark_comparison_service import build_benchmark_comparison


VALIDATED_CLAUSES = {
    "parties": {
        "status": "found",
        "extracted_text": "This Agreement is between Alpha LLC as Employer and Dana Smith as Employee.",
        "evidence_snippets": [{"quote": "between Alpha LLC as Employer and Dana Smith", "location": "section:Parties"}],
    },
    "compensation": {
        "status": "found",
        "extracted_text": "Employee will receive a monthly salary of 1,000 JOD paid at month end.",
        "evidence_snippets": [{"quote": "monthly salary of 1,000 JOD", "location": "section:Compensation"}],
    },
    "probation": {
        "status": "found",
        "extracted_text": "Probation Period: 3 months.",
        "evidence_snippets": [{"quote": "Probation Period: 3 months", "location": "section:Probation"}],
    },
    "termination": {
        "status": "found",
        "extracted_text": "Either party may terminate with 30 days written notice.",
        "evidence_snippets": [{"quote": "30 days written notice", "location": "section:Termination"}],
    },
    "leave_policy": {"status": "not_found", "extracted_text": None, "evidence_snippets": []},
}


def test_benchmark_service_output_schema_and_rule_basis():
    result = build_benchmark_comparison(
        contract_id="c1",
        validated_clauses=VALIDATED_CLAUSES,
        contract_type="employment",
        ai_commentary_fn=lambda _: "Plain-English AI commentary.",
    )
    assert result["benchmark_title"] == "Benchmark Comparison"
    assert result["benchmark_context"]["benchmark_basis"].lower().startswith("rule-based")
    assert "overall_position" in result
    assert "your_contract_vs_benchmark" in result
    assert "market_terms_comparison" in result
    assert result["ai_commentary"] == "Plain-English AI commentary."


def test_benchmark_does_not_fake_salary_market_average():
    result = build_benchmark_comparison(contract_id="c1", validated_clauses=VALIDATED_CLAUSES, contract_type="employment")
    salary = next(t for t in result["market_terms_comparison"] if t["term"] == "Monthly Salary")
    assert "no salary benchmark dataset" in salary["benchmark_average"].lower()
    assert salary["limitations"] == "Rule-based benchmark, not live market data."


def test_market_terms_found_and_missing():
    result = build_benchmark_comparison(contract_id="c1", validated_clauses=VALIDATED_CLAUSES, contract_type="employment")
    probation = next(t for t in result["market_terms_comparison"] if t["term"] == "Probation Period")
    leave = next(t for t in result["market_terms_comparison"] if t["term"] == "Annual Leave Days")
    assert probation["interpretation"] == "Aligned"
    assert leave["your_contract"].startswith("Not found")
    assert "unavailable" in leave["interpretation"].lower()


def test_ai_commentary_failure_falls_back():
    def fail(_payload):
        raise RuntimeError("llm down")

    result = build_benchmark_comparison(contract_id="c1", validated_clauses=VALIDATED_CLAUSES, contract_type="employment", ai_commentary_fn=fail)
    assert "AI commentary unavailable" in result["ai_commentary"]


def test_missing_benchmark_baseline_raises_when_baselines_unavailable(monkeypatch):
    import backend.services.benchmark_comparison_service as svc

    monkeypatch.setitem(svc.BASELINES, "general", None)
    with pytest.raises(ValueError):
        build_benchmark_comparison(contract_id="c1", validated_clauses={}, contract_type="weird")


def test_benchmark_rows_include_business_friendly_reporting_fields():
    result = build_benchmark_comparison(contract_id="c1", validated_clauses=VALIDATED_CLAUSES, contract_type="employment")
    row = result["your_contract_vs_benchmark"][0]
    assert "clause_summary" in row
    assert "why_this_matters" in row
    assert "confidence_label" in row
    assert "outlier_label" in row
    assert "peer_group_size" in row
