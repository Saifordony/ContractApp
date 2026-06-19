from backend.services.contract_intelligence import (
    CHUNK_OVERLAP_MARKER,
    answer_contract_question,
    arabic_normalize,
    chunk_contract_text,
    detect_contract_language,
    extract_key_clauses,
    is_heading,
    retrieve_relevant_chunks,
    classify_question_intent,
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
        assert "status" in data["clauses"][key]
        assert "confidence" in data["clauses"][key]
        assert "extracted_text" in data["clauses"][key]
        assert "evidence_snippets" in data["clauses"][key]
        assert "issues" in data["clauses"][key]
        assert "recommended_action" in data["clauses"][key]


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


def test_intent_classifier_detects_leave_policy():
    intent = classify_question_intent("how many sick leave days do i have?")
    assert intent == "leave_policy"


def test_answer_includes_intent_for_grounded_response():
    result = answer_contract_question(SAMPLE_CONTRACT, "Which law governs this agreement?")
    assert result.get("intent") in {"governing_law", "general_contract"}


def test_arabic_response_language_returns_arabic_not_found_text():
    result = answer_contract_question(SAMPLE_CONTRACT, "هل توجد عقوبة تأخير؟", response_language="arabic")
    assert "غير موجود" in result["answer"] or result.get("confidence", 0) > 0


def test_arabic_out_of_scope_returns_arabic_scope_message():
    result = answer_contract_question(SAMPLE_CONTRACT, "لا اريد الذهاب للعمل غدا ماذا افعل؟", response_language="arabic")
    assert "العقد" in result["answer"]


def test_parties_rejects_job_description_noise():
    noisy_text = """
Experience with version control Git and agile development methodologies.
Strong problem-solving and communication skills.
Probation Period: 3 months.
Confidentiality: Employees must keep company information confidential.
"""
    data = extract_key_clauses(noisy_text)
    parties = data["clauses"]["parties"]
    assert parties["status"] == "not_found"
    assert parties["extracted_text"] is None
    assert parties["evidence_snippets"] == []
    assert any("skills/job-description" in issue for issue in parties["issues"])


def test_extracted_clause_records_include_plain_english_fields():
    result = extract_key_clauses("This Agreement may be terminated by either party with 30 days written notice.")
    termination = result["clauses"]["termination"]
    assert "plain_english_summary" in termination
    assert "what_was_found" in termination
    assert "why_it_matters" in termination
    assert "missing_information" in termination


def test_arabic_clause_classification_finds_key_terms():
    arabic_contract = """
    ينص العقد على أن المقابل المالي يدفع خلال ثلاثين يوماً.
    يجوز إنهاء العقد بإشعار خطي مدته ثلاثون يوماً.
    تخضع هذه الاتفاقية إلى القانون الواجب التطبيق في الأردن.
    تتم تسوية النزاعات عن طريق التحكيم.
    تعتبر المعلومات السرية محمية طوال مدة العقد.
    """
    data = extract_key_clauses(arabic_contract)
    assert data["clauses"]["payment_terms"]["status"] == "found"
    assert data["clauses"]["termination"]["status"] == "found"
    assert data["clauses"]["governing_law"]["status"] == "found"
    assert data["clauses"]["dispute_resolution"]["status"] == "found"
    assert data["clauses"]["confidentiality"]["status"] == "found"


def test_arabic_normalize():
    # Alef variants (أ إ آ) fold to bare alef.
    assert arabic_normalize("أإآا") == "اااا"
    # Harakat / diacritics are stripped.
    assert arabic_normalize("سَلَام") == "سلام"
    # Teh marbuta (ة) maps to heh (ه).
    assert arabic_normalize("سيارة") == "سياره"
    # Yeh variant (ى) folds to yeh (ي).
    assert arabic_normalize("مستشفى") == "مستشفي"
    # Latin text passes through unchanged (case preserved).
    assert arabic_normalize("Payment Terms") == "Payment Terms"


def test_heading_detection_arabic():
    assert is_heading("المادة الخامسة: إنهاء العقد")
    assert is_heading("المادة الخامسة")
    assert is_heading("Article 5: Termination")
    assert is_heading("Section 3 Confidentiality")
    assert not is_heading("This is an ordinary sentence of contract body text.")


def test_chunk_arabic_only_text():
    arabic_contract = """اتفاقية عمل
المادة الأولى: الأطراف
هذه الاتفاقية مبرمة بين الشركة والموظف.
المادة الثانية: الأجر
يتقاضى الموظف راتباً شهرياً قدره ألف دينار.
المادة الثالثة: الإنهاء
يجوز إنهاء العقد بإشعار خطي مدته ثلاثون يوماً.
"""
    chunks = chunk_contract_text(arabic_contract)
    assert chunks, "Arabic-only text must produce at least one chunk"
    joined = "\n".join(c.text for c in chunks)
    assert "المادة" in joined
    assert "راتب" in joined


def test_chunk_overlap_present():
    # Body lines must not look like headings (no leading article/section/clause,
    # no trailing colon) so they accumulate into size-based chunks.
    body = "\n".join(f"the parties agree that obligation number {i} shall be performed in full." for i in range(60))
    text = "MASTER AGREEMENT\n" + body
    chunks = chunk_contract_text(text)
    assert len(chunks) >= 2, "text should span multiple chunks"
    # Overlap continuation marker appears in a downstream chunk.
    assert any(CHUNK_OVERLAP_MARKER in c.text for c in chunks[1:])
    # The last 2 non-empty lines of chunk N appear at the start of chunk N+1.
    prev_tail = [ln for ln in chunks[0].text.splitlines() if ln.strip()][-2:]
    for line in prev_tail:
        assert line in chunks[1].text


def test_detect_contract_language():
    assert detect_contract_language("This Agreement is governed by the laws of Jordan.") == "english"
    assert detect_contract_language("هذه الاتفاقية تخضع للقانون الأردني وكل أحكامه.") == "arabic"
    assert detect_contract_language("Governing Law: القانون الأردني applies to this Agreement fully.") == "bilingual"
    assert detect_contract_language("") == "english"
