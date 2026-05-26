from backend.services.contract_extraction_service import extract_clauses_with_validation, segment_contract_text


def _get_clause(result, key):
    return next(x for x in result["clause_results"] if x["clause_key"] == key)


def test_noise_text_not_force_filled():
    text = "Experience with Git. Strong problem-solving skills. Agile development methodologies."
    result = extract_clauses_with_validation(text)
    assert _get_clause(result, "parties")["status"] == "not_found"
    if any(x["clause_key"] == "compensation" for x in result["clause_results"]):
        assert _get_clause(result, "compensation")["status"] == "not_found"


def test_parties_found_with_direct_evidence():
    text = "This Employment Agreement is entered into between ABC Company as Employer and John Smith as Employee."
    result = extract_clauses_with_validation(text)
    parties = _get_clause(result, "parties")
    assert parties["status"] in {"found", "partially_found"}
    assert parties["evidence_snippets"]


def test_compensation_found_with_monthly_salary():
    text = "Employee shall receive a monthly salary of 2,000 JOD payable at the end of each month."
    result = extract_clauses_with_validation(text)
    clause = _get_clause(result, "compensation")
    assert clause["status"] in {"found", "partially_found"}


def test_termination_and_notice_detected():
    text = "Employee employment may be terminated by either party with 30 days written notice."
    result = extract_clauses_with_validation(text)
    termination = _get_clause(result, "termination")
    notice = _get_clause(result, "notice_period")
    assert termination["status"] in {"found", "partially_found"}
    assert notice["status"] in {"found", "partially_found", "needs_review"}


def test_governing_law_not_found_when_absent():
    text = "This agreement includes confidentiality obligations and payment terms only."
    result = extract_clauses_with_validation(text)
    law = _get_clause(result, "governing_law")
    assert law["status"] == "not_found"


def test_segmentation_returns_chunks():
    chunks = segment_contract_text("SECTION 1\nPayment terms apply.\nSECTION 2\nTermination by notice.")
    assert chunks
    assert chunks[0].chunk_id.startswith("chunk_")
