from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_arabic_pdf_renderer_uses_font_shaping_and_rtl_support():
    report = read("backend/services/report_service.py")
    for token in [
        "arabic_reshaper",
        "get_display",
        "TTFont",
        "NotoNaskhArabic",
        "NotoSansArabic",
        "DejaVuSans",
        "wordWrap=\"RTL\"",
        "TA_RIGHT",
        "_shape_arabic_markup",
        "مراجعة مدعومة بالذكاء الاصطناعي",
    ]:
        assert token in report


def test_docker_and_requirements_include_arabic_pdf_runtime_dependencies():
    requirements = read("requirements.txt")
    backend_dockerfile = read("Dockerfile.backend")
    frontend_dockerfile = read("Dockerfile.frontend")
    for token in ["arabic-reshaper", "python-bidi"]:
        assert token in requirements
    for token in ["fonts-dejavu-core", "fonts-noto-core"]:
        assert token in backend_dockerfile
        assert token in frontend_dockerfile


def test_arabic_pdf_generation_smoke_when_pdf_dependencies_are_installed():
    pytest.importorskip("reportlab")
    pytest.importorskip("arabic_reshaper")
    pytest.importorskip("bidi")

    from backend.services.report_service import generate_analysis_pdf

    pdf = generate_analysis_pdf(
        {"name": "Employment Agreement", "filename": "employment.pdf"},
        {
            "source": "hybrid",
            "llm_used": True,
            "active_model": "llama3.1:8b",
            "health_score": 82,
            "risk_level": "Medium",
            "ai_status": "LLM analysis completed",
            "executive_summary": "هذا ملخص تنفيذي مبسط للعقد.",
            "review_decision": {
                "review_decision": "يحتاج إلى مراجعة",
                "decision_confidence": "متوسطة",
                "decision_reasoning": "توجد بنود واضحة، لكن بعض التفاصيل تحتاج إلى تأكيد.",
            },
            "key_terms": [
                {
                    "term": "الإجازة السنوية",
                    "extracted_value": "21 يوم عمل",
                    "simple_explanation": "هذا يعني أن الموظف يحصل على إجازة سنوية مدفوعة.",
                    "risk_or_verify": "تأكد من رصيد الإجازة وآلية الموافقة.",
                    "evidence": [{"text": "The Employee is entitled to 21 working days of paid annual leave."}],
                }
            ],
            "clauses": [
                {
                    "title": "Leave Policy",
                    "status": "Found",
                    "review_priority": "Medium",
                    "simple_explanation": "هذا البند يشرح حق الإجازة السنوية.",
                    "why_it_matters": "يساعد على فهم حق الموظف في الإجازة.",
                    "risk_in_plain_english": "قد تحتاج الموافقة والرصيد إلى تأكيد.",
                    "ai_recommendation": "اسأل الموارد البشرية عن الرصيد المتاح.",
                    "negotiation_note": "يمكن توضيح إجراءات الموافقة.",
                    "evidence": [{"text": "The Employee is entitled to 21 working days of paid annual leave."}],
                }
            ],
            "evidence_trace": [
                {
                    "clause": "Leave Policy",
                    "source": "Extracted contract text",
                    "keyword": "annual leave",
                    "text": "The Employee is entitled to 21 working days of paid annual leave.",
                }
            ],
        },
        "2026-06-21",
        language="ar",
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
