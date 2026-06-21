import importlib
import sys
import types


def load_chat_service():
    sys.modules["requests"] = types.SimpleNamespace(
        get=lambda *args, **kwargs: types.SimpleNamespace(ok=False, status_code=503),
        post=lambda *args, **kwargs: types.SimpleNamespace(ok=False, status_code=503),
    )
    sys.modules["backend.config"] = types.SimpleNamespace(
        get_settings=lambda: types.SimpleNamespace(ollama_base_url="http://ollama:11434", ollama_model="llama3.1:8b")
    )
    return importlib.reload(importlib.import_module("backend.services.chat_service"))


CONTRACT_TEXT = """
The Employee is entitled to 21 working days of paid annual leave per completed year of service,
subject to scheduling approval by the Employer. Salary is SAR 18,000 gross monthly salary paid
monthly in arrears by bank transfer. Either party may terminate employment subject to the
termination clause and return of company property.
"""


def test_arabic_contract_questions_are_classified_as_contract_specific():
    chat = load_chat_service()
    assert chat.normalize_arabic_query("ممكن آخذ إجازة 10 أيام؟") == "ممكن اخذ اجازة 10 ايام"
    for question in [
        "ممكن اخذ اجازة 10 ايام",
        "كم يوم اجازة عندي؟",
        "هل اقدر ازيد راتبي؟",
        "اشرح لي بند الانهاء",
    ]:
        assert chat.classify_question(question) == "contract_specific"
    assert chat.classify_question("ما معنى الإجازة السنوية؟") == "general_contract_concept"
    assert chat.classify_question("مرحبا") == "small_talk"


def test_arabic_leave_chat_uses_selected_contract_evidence_and_arabic_answer():
    chat = load_chat_service()
    response = chat.answer_question(CONTRACT_TEXT, "ممكن اخذ اجازة 10 ايام", explanation_language="ar")
    assert response["answer_type"] == "contract_specific"
    assert response["used_contract"] is True
    assert response["response_language"] == "ar"
    assert "إجازة" in response["answer"] or "اجازة" in response["answer"]
    assert "UNRELATED_GENERAL" not in response["answer"]
    assert "No contract evidence was used" not in response["answer"]
    assert any("annual leave" in item["text"].lower() for item in response["evidence"])
    assert all(any("\u0600" <= char <= "\u06ff" for char in suggestion) for suggestion in response["follow_up_suggestions"])


def test_arabic_salary_and_termination_retrieval_bridge_to_english_contract_text():
    chat = load_chat_service()
    salary_evidence = chat.retrieve_evidence(CONTRACT_TEXT, "هل اقدر ازيد راتبي؟")
    termination_evidence = chat.retrieve_evidence(CONTRACT_TEXT, "اشرح لي بند الانهاء")
    assert any("salary" in item["text"].lower() for item in salary_evidence)
    assert any("terminate" in item["text"].lower() or "termination" in item["text"].lower() for item in termination_evidence)
