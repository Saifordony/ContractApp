from backend.services.contract_health import (
    evaluate_contract_health_from_clauses,
    infer_contract_type_from_clauses,
)


def test_contract_health_scores_and_flags_unlimited_liability():
    clauses = {
        "Payment Terms Clause": "Payment due within 30 days.",
        "Termination Clause": "Either party may terminate with 30 days notice.",
        "Governing Law": "Laws of New York apply.",
        "Dispute Resolution Clause": "Disputes resolved by arbitration.",
        "Liability": "Supplier has unlimited liability without limitation.",
        "Confidentiality Clause": "Both parties must keep information confidential.",
        "Scope of Work Clause": "Vendor provides implementation services.",
    }

    result = evaluate_contract_health_from_clauses(clauses)
    assert "health_score" in result
    assert "dimensions" in result
    assert any(flag["type"] == "unlimited_liability" for flag in result["red_flags"])
    assert result["risk_level"] in {"low", "medium", "high"}
    assert result["contract_type"] in {"service_agreement", "general_commercial"}


def test_contract_health_missing_governing_law_flagged():
    clauses = {
        "Payment Terms Clause": "Net 30",
        "Termination Clause": "30 day notice",
    }
    result = evaluate_contract_health_from_clauses(clauses)
    assert any("missing_governing_law" in issue for issue in result["issues"])


def test_contract_type_detection_employment_contract():
    clauses = {
        "Role": "Employee will work as software engineer.",
        "Compensation": "Employee salary is 5000 monthly.",
        "Benefits": "Paid leave and health insurance.",
        "Termination": "Employer may terminate for cause.",
    }
    detected = infer_contract_type_from_clauses(clauses)
    assert detected["contract_type"] == "employment"
    assert 0 <= detected["confidence"] <= 1


def test_contract_health_arabic_reasoning_when_language_arabic():
    clauses = {
        "Payment Terms Clause": "Net 30",
        "Termination Clause": "30 day notice",
    }
    result = evaluate_contract_health_from_clauses(clauses, response_language="arabic")
    assert "درجة" in result["reasoning"] or "العقد" in result["reasoning"]
