from backend.services.contract_chat_service import build_contract_chat_response, classify_chat_intent


CONTRACT_TEXT = """
EMPLOYMENT AGREEMENT
1. Parties
This Agreement is between Alpha LLC as Employer and Dana Smith as Employee.
2. Termination
Either party may terminate employment with 30 days written notice.
3. Compensation
Employee will receive a monthly salary of 1,000 JOD.
"""

ANALYSIS_RESULTS = {
    "structured_clauses": {
        "clauses": {
            "parties": {
                "status": "found",
                "extracted_text": "This Agreement is between Alpha LLC as Employer and Dana Smith as Employee.",
                "evidence_snippets": [{"quote": "between Alpha LLC as Employer and Dana Smith as Employee", "location": "section:Parties"}],
            },
            "termination": {
                "status": "found",
                "extracted_text": "Either party may terminate employment with 30 days written notice.",
                "evidence_snippets": [{"quote": "terminate employment with 30 days written notice", "location": "section:Termination"}],
            },
            "leave_policy": {
                "status": "not_found",
                "extracted_text": None,
                "evidence_snippets": [],
            },
        }
    },
    "health_evaluation": {
        "missing_critical_clauses": ["Governing Law"],
        "issues": ["Leave policy is not clear."],
        "required_changes": ["Add governing law and leave policy."],
    },
}


def test_chat_intent_detects_greeting_and_short_clause_lookup():
    assert classify_chat_intent("hi")[0] == "greeting"
    assert classify_chat_intent("vacation") == ("clause_lookup", "leave_policy")


def test_greeting_returns_warm_schema():
    result = build_contract_chat_response(message="hi", contract_text=CONTRACT_TEXT, analysis_results=ANALYSIS_RESULTS)
    assert result["answer_type"] == "greeting"
    assert result["confidence"] == "High"
    assert "I can help you review this contract" in result["answer"]
    assert isinstance(result["suggested_followups"], list)


def test_missing_vacation_clause_is_clear_without_hallucination():
    result = build_contract_chat_response(message="vacation", contract_text=CONTRACT_TEXT, analysis_results=ANALYSIS_RESULTS)
    assert result["answer_type"] == "missing_evidence"
    assert "could not find reliable evidence" in result["answer"]
    assert "vacation" in result["answer"].lower() or "leave" in result["answer"].lower()


def test_found_clause_response_includes_evidence():
    result = build_contract_chat_response(message="Explain termination", contract_text=CONTRACT_TEXT, analysis_results=ANALYSIS_RESULTS)
    assert result["answer_type"] == "grounded_answer"
    assert result["confidence"] == "High"
    assert result["evidence_snippets"]
    assert "30 days" in result["evidence_snippets"][0]["quote"]


def test_unrelated_question_redirects_to_contract():
    result = build_contract_chat_response(message="What should I cook for dinner tonight?", contract_text=CONTRACT_TEXT, analysis_results=ANALYSIS_RESULTS)
    assert result["answer_type"] == "unrelated"
    assert "uploaded contract" in result["answer"]


def test_debug_includes_history_count_only_when_enabled():
    result = build_contract_chat_response(
        message="risks",
        contract_text=CONTRACT_TEXT,
        analysis_results=ANALYSIS_RESULTS,
        chat_history=[{"role": "user", "content": "hi"}],
        debug=True,
    )
    assert result["debug"]["history_count"] == 1
