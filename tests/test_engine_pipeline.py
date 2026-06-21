import importlib
import sys
import types


def load_analysis_service():
    sys.modules["requests"] = types.SimpleNamespace(
        get=lambda *args, **kwargs: types.SimpleNamespace(ok=False, status_code=503),
        post=lambda *args, **kwargs: types.SimpleNamespace(ok=False, status_code=503),
    )
    sys.modules["backend.config"] = types.SimpleNamespace(
        get_settings=lambda: types.SimpleNamespace(ollama_base_url="http://ollama:11434", ollama_model="llama3.1:8b")
    )
    return importlib.reload(importlib.import_module("backend.services.analysis_service"))


def test_contract_type_detection_english_and_arabic():
    svc = load_analysis_service()
    english = "This Employment Agreement is between Employer and Employee. Salary, annual leave, probation and working hours apply."
    arabic = "عقد عمل بين صاحب العمل والموظف. يحدد هذا العقد الراتب والإجازة وفترة التجربة وساعات العمل."
    assert svc.detect_contract_type(english)["contract_type"] == "employment"
    assert svc.detect_contract_type(arabic)["contract_type"] == "employment"


def test_arabic_clause_detection_returns_meaningful_clauses():
    svc = load_analysis_service()
    text = """
    المادة الأولى: الأطراف
    تم الاتفاق بين صاحب العمل والموظف.
    المادة الثانية: الراتب
    يستحق الموظف الراتب شهرياً.
    المادة الثالثة: الإنهاء
    يجوز إنهاء العقد بإشعار خطي.
    المادة الرابعة: السرية
    يلتزم الموظف بالمحافظة على المعلومات السرية وعدم الإفصاح.
    المادة الخامسة: القانون الحاكم
    يخضع هذا العقد للقانون الحاكم والاختصاص أمام المحكمة المختصة.
    """
    result = svc.analyze_text(text, explanation_language="ar", ui_language="ar")
    found = {clause["type"] for clause in result["clauses"] if clause["found"]}
    assert {"parties", "payment", "termination", "confidentiality", "governing_law"}.issubset(found)
    assert result["contract_language"] == "ar"
    assert result["contract_type"] == "employment"


def test_section_parser_preserves_references_and_offsets():
    svc = load_analysis_service()
    text = "1. Payment\nThe Client shall pay monthly fees.\n\nArticle 2: Termination\nEither party may terminate with notice."
    sections = svc.parse_contract_sections(text)
    assert sections
    assert all("start_char" in section and "end_char" in section for section in sections)
    assert any("Payment" in section["section_title"] for section in sections)


def test_text_extraction_metadata_for_txt():
    svc = load_analysis_service()
    extracted = svc.extract_contract_text("sample.txt", b"Contract text")
    assert extracted["text"] == "Contract text"
    assert extracted["extraction_method"] == "text"
    assert extracted["warnings"] == []
