import json
from pathlib import Path

from backend.services.benchmark_service import (
    BenchmarkAnalyzeResponse,
    classify_clause_type,
    extract_numeric_features,
    ingest_seed_dataset,
    load_seed_from_repo,
    run_benchmark_analysis,
    split_clauses,
    _compute_percentiles,
)


def test_clause_splitter_stable_output():
    text = """
    MASTER SERVICES AGREEMENT
    PAYMENT TERMS
    Invoices due within 30 days.
    TERMINATION
    Either party may terminate with 30 days notice.
    """
    clauses = split_clauses(text)
    assert len(clauses) >= 2
    assert any("payment" in c[0] for c in clauses)


def test_clause_classifier_expected_labels():
    assert classify_clause_type("Payment Terms", "invoice due in 30 days") == "payment_terms"
    assert classify_clause_type("Termination", "terminate with notice") == "termination"
    assert classify_clause_type("Random", "hello world") == "misc"


def test_percentiles_computation():
    stats = _compute_percentiles([10, 20, 30, 40])
    assert stats["median"] == 25.0
    assert stats["p25"] == 10.0
    assert stats["p75"] == 30.0


def test_benchmark_analysis_integration_with_seed_fixture(tmp_path):
    # ensure seed loaded
    load_seed_from_repo()

    contract_text = Path("contract-analysis-platform/tests/fixtures/sample_contract.txt").read_text()
    result = run_benchmark_analysis(
        filename="sample_contract.txt",
        file_bytes=contract_text.encode(),
        contract_type="employment",
        jurisdiction="jordan",
        industry="technology",
        opt_in_store_user_data=False,
    )

    validated = BenchmarkAnalyzeResponse.model_validate(result)
    assert validated.clause_results
    high_conf = [c for c in validated.clause_results if c.confidence >= 0.5]
    if high_conf:
        assert any(c.citations for c in high_conf)


def test_no_evidence_case_is_low_confidence_and_not_green():
    ingest_seed_dataset([], clear_first=True)
    contract_text = "PART-TIME JOB RIGHTS. Employee may work another job freely."
    result = run_benchmark_analysis(
        filename="contract.txt",
        file_bytes=contract_text.encode(),
        contract_type="ultra_rare_type",
        jurisdiction="nowhere",
        industry="unknown",
        opt_in_store_user_data=False,
    )

    assert result["clause_results"]
    first = result["clause_results"][0]
    assert first["confidence"] <= 0.25
    assert first["alignment_label"] != "green"
    assert "Insufficient benchmark evidence" in first["explanation"]
