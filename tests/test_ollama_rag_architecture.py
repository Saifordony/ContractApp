import importlib
import sys
import types


def load_services():
    sys.modules["backend.config"] = types.SimpleNamespace(
        get_settings=lambda: types.SimpleNamespace(
            ollama_base_url="http://ollama:11434",
            ollama_model="llama3.1:8b",
            ollama_analysis_model="qwen3:14b",
            ollama_chat_model="qwen3:14b",
            ollama_review_model="deepseek-r1:14b",
            ollama_embed_model="bge-m3",
            ollama_fallback_model="llama3.1:8b",
            ollama_temperature=0.1,
            ollama_num_ctx=32768,
            ollama_timeout=120,
            ollama_enable_reviewer=True,
            ollama_enable_embeddings=True,
        )
    )
    llm = importlib.reload(importlib.import_module("backend.services.llm_service"))
    analysis = importlib.reload(importlib.import_module("backend.services.analysis_service"))
    chat = importlib.reload(importlib.import_module("backend.services.chat_service"))
    return llm, analysis, chat


def test_model_selection_falls_back_when_preferred_missing():
    llm, _, _ = load_services()
    selected = llm.select_available_model("qwen3:14b", "llama3.1:8b", ["llama3.1:8b"])
    assert selected["model"] == "llama3.1:8b"
    assert selected["fallback_used"] is True


def test_hybrid_retrieval_returns_metadata_for_english_and_arabic_sections():
    _, analysis, _ = load_services()
    text = """
    Article 1: Payment
    The Client shall pay monthly fees within 15 days of invoice.
    المادة الثانية: الإنهاء
    يجوز إنهاء العقد بإشعار خطي قبل ثلاثين يوماً.
    """
    chunks = analysis.parse_contract_sections(text)
    english = analysis.retrieve_evidence("c1", "payment invoice timing", chunks, clause_type="payment")
    arabic = analysis.retrieve_evidence("c1", "اشرح بند الانهاء", chunks, clause_type="termination")
    assert english and english[0]["chunk_id"] and "lexical_score" in english[0]
    assert arabic and any("إنهاء" in item["text"] or "انهاء" in item["text"] for item in arabic)


def test_chat_schema_and_no_hard_coded_leave_entitlement_when_evidence_missing():
    _, _, chat = load_services()
    response = chat.answer_question("This contract only says the employee must follow company policy.", "Can I take 10 days leave?", explanation_language="en")
    assert response["schema_validated"] is True
    assert response["used_contract"] is True
    assert "could not find contract evidence" in response["answer"].lower() or "does not show enough evidence" in response["answer"].lower()
    assert "you can" not in response["answer"].lower()
