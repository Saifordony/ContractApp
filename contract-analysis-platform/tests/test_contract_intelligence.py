from backend.services.contract_intelligence import (
    answer_contract_question,
    chunk_contract_text,
    extract_key_clauses,
    retrieve_relevant_chunks,
)


SAMPLE_CONTRACT = """
MASTER SERVICES AGREEMENT
1. Parties
This Agreement is between Alpha LLC and Beta Inc.
2. Payment Terms
Client shall pay $10,000 within 30 days of invoice.
3. Governing Law
This Agreement is governed by the laws of New York.
4. Termination
Either party may terminate with 30 days notice.
"""


def test_extraction_schema_has_required_fields():
    data = extract_key_clauses(SAMPLE_CONTRACT)
    assert "clauses" in data
    assert "conflicts" in data
    assert "chunk_count" in data
    assert isinstance(data["clauses"], dict)
    for key in ["payment_terms", "governing_law", "termination", "parties"]:
        assert key in data["clauses"]
        assert "value" in data["clauses"][key]
        assert "evidence" in data["clauses"][key]
        assert "status" in data["clauses"][key]


def test_retrieval_returns_relevant_chunk():
    chunks = chunk_contract_text(SAMPLE_CONTRACT)
    hits = retrieve_relevant_chunks("What are the payment terms?", chunks, top_k=2)
    assert hits
    assert any("pay $10,000" in h.text for h in hits)


def test_question_answer_contains_evidence_and_no_hallucinated_structure():
    result = answer_contract_question(SAMPLE_CONTRACT, "Which law governs this agreement?")
    assert "answer" in result
    assert "evidence" in result and isinstance(result["evidence"], list)
    assert result["evidence"], "must include evidence"
    assert all("location" in e and "quote" in e for e in result["evidence"])


def test_question_with_no_relevant_terms_returns_not_found():
    result = answer_contract_question(SAMPLE_CONTRACT, "Can I get a part-time job after working hours?")
    assert result["answer"].startswith("Not Found")
    assert result["not_found"]


def test_retrieval_handles_synonym_query_for_jurisdiction():
    chunks = chunk_contract_text(SAMPLE_CONTRACT)
    hits = retrieve_relevant_chunks("Which jurisdiction applies?", chunks, top_k=2)
    assert hits
    assert any("governed by the laws of New York" in h.text for h in hits)


def test_personal_nonlegal_question_returns_contract_scope_message():
    result = answer_contract_question(SAMPLE_CONTRACT, "i dont feel like going to work tomorrow what can i do ?")
    assert "contract-related" in result["answer"].lower()
    assert result["not_found"]
    assert result["confidence"] == 0.0
