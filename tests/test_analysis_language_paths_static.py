from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_arabic_questions_helper_is_defined_and_used_safely():
    src = read("backend/services/analysis_service.py")
    assert "def _arabic_questions_for_clause" in src
    assert "def _questions_for_clause" in src
    assert '_questions_for_clause(ctype, "ar")' in src
    for clause_type in [
        "termination",
        "payment",
        "confidentiality",
        "intellectual_property",
        "non_compete",
        "non_solicitation",
        "liability",
        "governing_law",
        "dispute_resolution",
    ]:
        assert f'"{clause_type}"' in src
    assert "هل يوضح العقد مدة الإشعار المطلوبة قبل الإنهاء؟" in src
    assert "ما الالتزامات الأساسية التي يفرضها هذا البند؟" in src


def test_analysis_language_contract_is_present_for_all_ui_explanation_combinations():
    src = read("backend/services/analysis_service.py")
    assert 'def analyze_text(text: str, explanation_language: str = "en", ui_language: str = "en")' in src
    assert "explanation_language" in src
    assert "ui_language" in src
    assert "questions_to_ask" in src
    assert "simple_explanation" in src
    assert "risk_in_plain_english" in src
    assert "recommended_fix" in src
    assert "negotiation_note" in src


def test_contract_analysis_errors_return_language_metadata():
    contracts = read("backend/routers/contracts.py")
    frontend = read("frontend/streamlit_app.py")
    assert "ANALYSIS_LANGUAGE_HELPER_ERROR" in contracts
    assert "explanation_language" in contracts and "ui_language" in contracts
    assert "Arabic analysis failed due to a backend language helper error" in contracts
    assert "error_code" in frontend
    assert "explanation_language" in frontend and "ui_language" in frontend
