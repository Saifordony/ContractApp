from backend.services.contract_health import evaluate_contract_health_from_clauses


def test_contract_health_scores_and_flags_unlimited_liability():
    clauses = {
        "Payment Terms Clause": "Payment due within 30 days.",
        "Termination Clause": "Either party may terminate with 30 days notice.",
        "Governing Law": "Laws of New York apply.",
        "Dispute Resolution Clause": "Disputes resolved by arbitration.",
        "Liability": "Supplier has unlimited liability without limitation.",
        "Confidentiality Clause": "Both parties must keep information confidential.",
    }

    result = evaluate_contract_health_from_clauses(clauses)
    assert "health_score" in result
    assert "dimensions" in result
    assert any(flag["type"] == "unlimited_liability" for flag in result["red_flags"])
    assert result["risk_level"] in {"low", "medium", "high"}


def test_contract_health_missing_governing_law_flagged():
    clauses = {
        "Payment Terms Clause": "Net 30",
        "Termination Clause": "30 day notice",
    }
    result = evaluate_contract_health_from_clauses(clauses)
    assert any("governing" in issue for issue in result["issues"])
