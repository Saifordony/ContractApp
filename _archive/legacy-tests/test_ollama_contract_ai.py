from backend.services.benchmark_comparison_service import build_benchmark_comparison
from backend.services.contract_health import evaluate_contract_health_from_clauses
from backend.services.ollama_contract_ai import (
    build_clause_memory,
    classify_contract_task,
    compute_confidence,
    hybrid_retrieve_evidence,
    parse_json_lenient,
    reviewer_verification,
    run_contract_reasoning_pipeline,
    validate_ai_json_schema,
)


CONTRACT_TEXT = """
MASTER SERVICES AGREEMENT
1. Payment Terms
The Client will pay the Provider monthly within 30 days after receiving a valid invoice.
2. Termination
Either party may terminate this Agreement by giving 30 days written notice.
3. Confidentiality
Each party must protect confidential information for three years after termination.
4. Governing Law
This Agreement is governed by the laws of Jordan.
"""


def test_task_classification_supports_contract_analysis_intents():
    assert classify_contract_task("summarize this contract") == "summary"
    assert classify_contract_task("what benchmark gaps matter?") == "benchmark_explanation"
    assert classify_contract_task("is this safe to sign?") == "risk_review"


def test_hybrid_retrieval_prioritizes_relevant_clause_titles():
    hits = hybrid_retrieve_evidence(CONTRACT_TEXT, "termination notice", top_k=2)
    assert hits
    assert "terminate" in hits[0]["quote"].lower() or "termination" in hits[0]["quote"].lower()
    assert hits[0]["relevance_score"] > 0


def test_clause_memory_uses_validated_clauses_and_tracks_missing_items():
    memory = build_clause_memory(
        CONTRACT_TEXT,
        {
            "termination": {
                "status": "found",
                "extracted_text": "Either party may terminate with 30 days written notice.",
                "evidence_snippets": [{"quote": "30 days written notice", "location": "section:Termination"}],
            }
        },
    )
    assert memory["termination"][0]["source"] == "validated_clause"
    assert "payment_terms" in memory
    assert "missing_clauses" in memory


def test_json_schema_validation_and_lenient_parsing():
    payload = parse_json_lenient("```json\n{'answer': 'OK', 'confidence': 2, 'evidence': {'quote': 'x'}}\n```")
    normalized = validate_ai_json_schema(payload)
    assert normalized["answer"] == "OK"
    assert normalized["confidence"] == 1.0
    assert isinstance(normalized["evidence"], list)
    assert isinstance(normalized["risks"], list)
    assert isinstance(normalized["missing_information"], list)


def test_reviewer_rejects_unsupported_answer_without_evidence():
    review = reviewer_verification({"answer": "The contract has a 20 day leave policy.", "evidence": []}, [])
    assert review["approved"] is False
    assert review["unsupported_claims"]


def test_not_found_behavior_when_evidence_is_missing():
    result = run_contract_reasoning_pipeline(question="vacation leave", contract_text="This contract only mentions payment terms.")
    assert result["answer"] == "Not found in the provided contract text."
    assert result["confidence"] <= 0.1
    assert result["missing_information"]


def test_grounded_pipeline_returns_evidence_quotes_for_found_answer():
    result = run_contract_reasoning_pipeline(question="termination notice", contract_text=CONTRACT_TEXT)
    assert result["evidence"]
    assert any("termination" in item["quote"].lower() or "terminate" in item["quote"].lower() for item in result["evidence"])
    assert result["confidence"] > 0.1


def test_invalid_json_uses_repair_prompt_then_validates():
    calls = []

    def fake_llm(prompt: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return "not json"
        return '{"answer":"Payment is due within 30 days.","confidence":0.7,"evidence":[{"quote":"within 30 days","location":"section:Payment"}],"risks":[],"missing_information":[]}'

    result = run_contract_reasoning_pipeline(question="payment terms", contract_text=CONTRACT_TEXT, llm_callable=fake_llm, debug=True)
    assert len(calls) == 2
    assert result["answer"].startswith("Payment")
    assert result["debug"]["json_repaired_or_fallback"] is True


def test_confidence_scoring_requires_evidence_and_reviewer_approval():
    no_evidence = compute_confidence(evidence_count=0, best_relevance=0.8)
    approved = compute_confidence(evidence_count=3, best_relevance=0.8, reviewer_approved=True)
    rejected = compute_confidence(evidence_count=3, best_relevance=0.8, reviewer_approved=False)
    assert no_evidence < rejected < approved


def test_compute_confidence_zero_evidence():
    assert compute_confidence(evidence_count=0, best_relevance=0.9) == 0.05


def test_compute_confidence_max_evidence():
    capped = compute_confidence(evidence_count=50, best_relevance=1.0, reviewer_approved=True)
    assert capped == 0.95


def test_reviewer_verification_missing_evidence_key():
    # Payload deliberately omits the "evidence" key entirely.
    review = reviewer_verification(
        {"answer": "Payment is due within 30 days."},
        [{"quote": "within 30 days", "location": "section:Payment"}],
    )
    assert isinstance(review, dict)
    assert "approved" in review
    # No citations in the payload -> not approved, but no crash.
    assert review["approved"] is False


def test_json_repair_path_activated():
    calls = []

    def fake_llm(prompt: str) -> str:
        calls.append(prompt)
        if len(calls) <= 3:  # all 3 attempts (MAX_RETRIES + 1) fail
            return "definitely not json"
        return (
            '{"answer":"Payment is due within 30 days.","confidence":0.7,'
            '"evidence":[{"quote":"within 30 days","location":"section:Payment"}],'
            '"risks":[],"missing_information":[]}'
        )

    result = run_contract_reasoning_pipeline(
        question="payment terms", contract_text=CONTRACT_TEXT, llm_callable=fake_llm, debug=True
    )
    assert len(calls) == 4  # 3 failed attempts + 1 repair call
    assert result["answer"].startswith("Payment")
    assert result["debug"]["json_repaired_or_fallback"] is True


def test_retry_loop_exhausted_falls_back():
    calls = []

    def always_bad(prompt: str) -> str:
        calls.append(prompt)
        return "still not json"

    result = run_contract_reasoning_pipeline(
        question="payment terms", contract_text=CONTRACT_TEXT, llm_callable=always_bad, debug=True
    )
    # 3 attempts + 1 repair attempt, then deterministic fallback.
    assert len(calls) == 4
    assert result["evidence"], "deterministic fallback still surfaces grounded evidence"
    assert result["debug"]["json_repaired_or_fallback"] is True


def test_contract_health_and_benchmark_outputs_remain_separate():
    clauses = {
        "payment_terms": "The Client will pay monthly within 30 days after invoice.",
        "termination": "Either party may terminate with 30 days written notice.",
        "governing_law": "This Agreement is governed by Jordanian law.",
    }
    health = evaluate_contract_health_from_clauses(clauses)
    benchmark = build_benchmark_comparison(
        contract_id="c1",
        validated_clauses={key: {"status": "found", "extracted_text": value, "evidence_snippets": []} for key, value in clauses.items()},
        contract_type="service_agreement",
    )
    assert health["module"] == "contract_health"
    assert "dimensions" in health
    assert all("supporting_evidence" in item and "recommended_action" in item for item in health["dimensions"])
    assert benchmark["benchmark_title"] == "Benchmark Comparison"
    assert "overall_position" in benchmark
