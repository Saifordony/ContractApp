"""PDF report generation for contract analysis results."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
TAG_RE = re.compile(r"(<[^>]+>)")
ARABIC_FONT_NAME = "ContractArabicFont"


def _find_arabic_font() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/NotoNaskhArabic-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _register_arabic_font() -> str:
    font_path = _find_arabic_font()
    if not font_path:
        return "Helvetica"
    try:
        if ARABIC_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(ARABIC_FONT_NAME, font_path))
        return ARABIC_FONT_NAME
    except Exception:
        return "Helvetica"


def _shape_arabic_segment(text: str) -> str:
    if not ARABIC_RE.search(text):
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def _shape_arabic_markup(text: str, enabled: bool) -> str:
    if not enabled:
        return text
    parts = TAG_RE.split(text)
    return "".join(part if part.startswith("<") and part.endswith(">") else _shape_arabic_segment(part) for part in parts)


def _escape_pdf_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _text(value: Any, fallback: str = "Not specified") -> str:
    if value is None:
        return fallback
    if isinstance(value, list):
        return "; ".join(_text(item, "") for item in value if _text(item, "")) or fallback
    if isinstance(value, dict):
        return "; ".join(f"{str(k).replace('_', ' ').title()}: {_text(v, '')}" for k, v in value.items() if _text(v, "")) or fallback
    result = str(value).strip()
    return result or fallback


def _evidence_text(evidence: Any) -> str:
    if isinstance(evidence, list) and evidence:
        first = evidence[0]
        if isinstance(first, dict):
            return _text(first.get("text") or first.get("snippet"), "No direct evidence captured.")
        return _text(first)
    return "No direct evidence captured."


def _para(text: Any, style: ParagraphStyle, *, arabic: bool = False, markup: bool = False) -> Paragraph:
    clean = _text(text)
    if not markup:
        clean = _escape_pdf_text(clean)
    clean = _shape_arabic_markup(clean, arabic)
    return Paragraph(clean, style)


def _section(story: list, title: str, styles, *, arabic: bool = False) -> None:
    story.append(Spacer(1, 0.18 * inch))
    story.append(_para(title, styles["SectionTitle"], arabic=arabic))
    story.append(Spacer(1, 0.08 * inch))


def _footer(canvas, doc):
    canvas.saveState()
    footer_font = getattr(doc, "footer_font", "Helvetica")
    footer_arabic = getattr(doc, "footer_arabic", False)
    footer_note = getattr(doc, "footer_note", "AI-assisted review only — not legal advice.")
    canvas.setFont(footer_font, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    if footer_arabic:
        shaped_note = _shape_arabic_markup(_escape_pdf_text(footer_note), True)
        canvas.drawRightString(A4[0] - 0.55 * inch, 0.38 * inch, shaped_note)
        canvas.drawString(0.55 * inch, 0.38 * inch, f"Page {doc.page}")
    else:
        canvas.drawString(0.55 * inch, 0.38 * inch, footer_note)
        canvas.drawRightString(A4[0] - 0.55 * inch, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def generate_analysis_pdf(contract: dict[str, Any], analysis: dict[str, Any], generated_at: str, language: str = "en") -> bytes:
    buffer = BytesIO()
    ar = language == "ar"
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.55 * inch, leftMargin=0.55 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch)
    base = getSampleStyleSheet()
    arabic_font = _register_arabic_font() if ar else "Helvetica"
    arabic_bold = arabic_font if ar else "Helvetica-Bold"
    align = TA_RIGHT if ar else TA_LEFT
    styles = {
        "Title": ParagraphStyle("ReportTitle", parent=base["Title"], fontName=arabic_bold, fontSize=24, leading=30, alignment=align, wordWrap="RTL" if ar else None, textColor=colors.HexColor("#0f172a"), spaceAfter=14),
        "Subtitle": ParagraphStyle("ReportSubtitle", parent=base["BodyText"], fontName=arabic_font, fontSize=10, leading=15, alignment=align, wordWrap="RTL" if ar else None, textColor=colors.HexColor("#475569")),
        "SectionTitle": ParagraphStyle("SectionTitle", parent=base["Heading2"], fontName=arabic_bold, fontSize=15, leading=19, alignment=align, wordWrap="RTL" if ar else None, textColor=colors.HexColor("#1d4ed8")),
        "Body": ParagraphStyle("ReportBody", parent=base["BodyText"], fontName=arabic_font, fontSize=9.5, leading=14, alignment=align, wordWrap="RTL" if ar else None, textColor=colors.HexColor("#0f172a")),
        "Small": ParagraphStyle("ReportSmall", parent=base["BodyText"], fontName=arabic_font, fontSize=8, leading=11, alignment=align, wordWrap="RTL" if ar else None, textColor=colors.HexColor("#475569")),
        "Quote": ParagraphStyle("EvidenceQuote", parent=base["BodyText"], fontName="Helvetica", fontSize=8.4, leading=12, alignment=TA_LEFT, leftIndent=10, borderColor=colors.HexColor("#bfdbfe"), borderWidth=1, borderPadding=6, backColor=colors.HexColor("#eff6ff")),
    }
    doc.footer_arabic = ar
    doc.footer_font = arabic_font
    doc.footer_note = "مراجعة مدعومة بالذكاء الاصطناعي — ليست رأيًا قانونيًا نهائيًا." if ar else "AI-assisted review only — not legal advice."
    labels = {
        "title": "تقرير ذكاء العقود" if ar else "Contract Intelligence Report",
        "date": "تاريخ الإنشاء" if ar else "Date generated",
        "ai_mode": "وضع الذكاء الاصطناعي" if ar else "AI mode",
        "llm_used": "تم استخدام النموذج" if ar else "LLM used",
        "model": "النموذج" if ar else "Model",
        "disclaimer": "هذا التقرير مراجعة مساعدة بالذكاء الاصطناعي وليس رأيًا قانونيًا نهائيًا. يجب إجراء مراجعة قانونية وتجارية بشرية قبل الاعتماد عليه." if ar else "Disclaimer: This report is an AI-assisted contract review and is not final legal advice. Human legal and business review is required before relying on it.",
        "exec": "1. الملخص التنفيذي" if ar else "1. Executive Summary",
        "terms": "2. البنود الرئيسية المستخرجة" if ar else "2. Key Terms Extracted",
        "decision": "3. قرار الذكاء الاصطناعي" if ar else "3. Overall AI Decision",
        "risks": "4. نظرة عامة على المخاطر" if ar else "4. Risk Overview",
        "clauses": "5. مراجعة البنود" if ar else "5. Clause-by-Clause Review",
        "missing": "6. البنود المفقودة أو الضعيفة" if ar else "6. Missing / Weak Clauses",
        "actions": "7. الإجراءات المقترحة" if ar else "7. Recommended Actions",
        "evidence": "8. ملحق الأدلة" if ar else "8. Evidence Appendix",
        "final_disclaimer": "9. تنبيه مهم" if ar else "9. Disclaimer",
        "overall_health": "الصحة العامة" if ar else "Overall health",
        "risk_level": "مستوى المخاطر" if ar else "Risk level",
        "ai_status": "حالة الذكاء الاصطناعي" if ar else "AI status",
        "explanation": "شرح مبسط" if ar else "Explanation",
        "verify": "ما يجب التحقق منه" if ar else "Verify",
        "evidence_label": "الدليل" if ar else "Evidence",
        "severity": "الخطورة" if ar else "Severity",
        "impact": "الأثر" if ar else "Impact",
        "recommended_action": "الإجراء المقترح" if ar else "Recommended action",
        "priority": "الأولوية" if ar else "Priority",
        "status": "الحالة" if ar else "Status",
        "simple_explanation": "شرح مبسط" if ar else "Simple explanation",
        "why_it_matters": "لماذا هذا مهم" if ar else "Why it matters",
        "risk_plain": "الخطر ببساطة" if ar else "Risk in plain English",
        "recommendation": "التوصية" if ar else "Recommendation",
        "negotiation_note": "ملاحظة تفاوضية" if ar else "Negotiation note",
        "no_key_terms": "لم يتم استخراج بنود رئيسية. أعد تشغيل التحليل باستخدام نسخة أوضح من العقد إذا بدا ذلك غير صحيح." if ar else "No key terms were extracted. Run analysis again with a clearer contract scan if this appears incorrect.",
        "no_risks": "لم يتم رصد مخاطر رئيسية من البنود المستخرجة." if ar else "No major risks were detected from the extracted clauses.",
        "missing_review": "راجع ما إذا كانت هذه الحماية يجب إضافتها أو تقويتها." if ar else "Review whether this protection should be added or strengthened.",
        "no_missing": "لم يحدد التحليل الحالي بنودًا حرجة مفقودة." if ar else "No missing critical clauses were identified by the current analysis.",
        "confirm_terms": "أكد البنود التجارية المستخرجة وأكمل المراجعة القانونية البشرية قبل التوقيع." if ar else "Confirm extracted business terms and complete human legal review before signature.",
    }
    story: list[Any] = []
    contract_name = _text(contract.get("name") or contract.get("filename"), "Untitled contract")
    story.append(_para(labels["title"], styles["Title"], arabic=ar))
    story.append(_para(contract_name, styles["SectionTitle"], arabic=ar))
    story.append(_para(f"{labels['date']}: {generated_at}", styles["Subtitle"], arabic=ar))
    story.append(_para(f"{labels['ai_mode']}: {_text(analysis.get('source'))} | {labels['llm_used']}: {_text(analysis.get('llm_used'))} | {labels['model']}: {_text(analysis.get('active_model'))}", styles["Subtitle"], arabic=ar))
    story.append(Spacer(1, 0.25 * inch))
    story.append(_para(labels["disclaimer"], styles["Body"], arabic=ar))
    story.append(PageBreak())

    _section(story, labels["exec"], styles, arabic=ar)
    summary_rows = [
        [_para(labels["overall_health"], styles["Small"], arabic=ar), _para(f"{_text(analysis.get('health_score'))}/100", styles["Small"], arabic=False)],
        [_para(labels["risk_level"], styles["Small"], arabic=ar), _para(_text(analysis.get("risk_level")), styles["Small"], arabic=ar)],
        [_para(labels["ai_status"], styles["Small"], arabic=ar), _para(_text(analysis.get("ai_status")), styles["Small"], arabic=ar)],
    ]
    story.append(Table(summary_rows, colWidths=[1.8 * inch, 4.6 * inch], style=TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")), ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#cbd5e1")), ("INNERGRID", (0, 0), (-1, -1), .25, colors.HexColor("#e2e8f0")), ("VALIGN", (0, 0), (-1, -1), "TOP")])) )
    story.append(Spacer(1, 0.12 * inch))
    story.append(_para(analysis.get("executive_summary"), styles["Body"], arabic=ar))

    decision = analysis.get("review_decision") or {}
    if isinstance(decision, dict) and decision:
        _section(story, labels["decision"], styles, arabic=ar)
        story.append(_para(f"{_text(decision.get('review_decision'))} — {_text(decision.get('decision_confidence'))}", styles["Body"], arabic=ar))
        story.append(_para(decision.get("decision_reasoning"), styles["Small"], arabic=ar))

    _section(story, labels["terms"], styles, arabic=ar)
    key_terms = analysis.get("key_terms") or []
    if key_terms:
        for term in key_terms:
            story.append(_para(f"<b>{_text(term.get('term'))}</b>: {_text(term.get('extracted_value'))}", styles["Body"], arabic=ar, markup=True))
            story.append(_para(f"<b>{labels['explanation']}:</b> {_text(term.get('simple_explanation'))}", styles["Small"], arabic=ar, markup=True))
            story.append(_para(f"<b>{labels['verify']}:</b> {_text(term.get('risk_or_verify'))}", styles["Small"], arabic=ar, markup=True))
            story.append(_para(f"{labels['evidence_label']}: {_evidence_text(term.get('evidence'))}", styles["Quote"], arabic=False))
            story.append(Spacer(1, 0.08 * inch))
    else:
        story.append(_para(labels["no_key_terms"], styles["Body"], arabic=ar))

    _section(story, labels["risks"], styles, arabic=ar)
    risks = analysis.get("risks") or []
    if risks:
        for risk in risks:
            story.append(_para(f"<b>{_text(risk.get('title'))}</b> — {labels['severity']}: {_text(risk.get('severity'))}", styles["Body"], arabic=ar, markup=True))
            story.append(_para(f"<b>{labels['impact']}:</b> {_text(risk.get('explanation'))}", styles["Small"], arabic=ar, markup=True))
            story.append(_para(f"<b>{labels['recommended_action']}:</b> {_text(risk.get('suggested_mitigation') or risk.get('recommendation'))}", styles["Small"], arabic=ar, markup=True))
            story.append(Spacer(1, 0.06 * inch))
    else:
        story.append(_para(labels["no_risks"], styles["Body"], arabic=ar))

    _section(story, labels["clauses"], styles, arabic=ar)
    for clause in analysis.get("clauses") or []:
        story.append(_para(f"<b>{_text(clause.get('title'))}</b> — {labels['status']}: {_text(clause.get('status'))} — {labels['priority']}: {_text(clause.get('review_priority'))}", styles["Body"], arabic=ar, markup=True))
        story.append(_para(f"{labels['evidence_label']}: {_evidence_text(clause.get('evidence'))}", styles["Quote"], arabic=False))
        for label, key in [(labels["simple_explanation"], "simple_explanation"), (labels["why_it_matters"], "why_it_matters"), (labels["risk_plain"], "risk_in_plain_english"), (labels["recommendation"], "ai_recommendation"), (labels["negotiation_note"], "negotiation_note")]:
            story.append(_para(f"<b>{label}:</b> {_text(clause.get(key))}", styles["Small"], arabic=ar, markup=True))
        story.append(Spacer(1, 0.12 * inch))

    _section(story, labels["missing"], styles, arabic=ar)
    missing = analysis.get("missing_critical_clauses") or analysis.get("missing_clauses") or []
    if missing:
        for item in missing:
            story.append(_para(f"<b>{_text(item).replace('_', ' ').title()}</b>: {labels['missing_review']}", styles["Body"], arabic=ar, markup=True))
    else:
        story.append(_para(labels["no_missing"], styles["Body"], arabic=ar))

    _section(story, labels["actions"], styles, arabic=ar)
    actions = analysis.get("recommended_actions") or analysis.get("recommended_improvements") or []
    if actions:
        for action in actions:
            story.append(_para(f"• {_text(action)}", styles["Body"], arabic=ar))
    else:
        story.append(_para(labels["confirm_terms"], styles["Body"], arabic=ar))

    _section(story, labels["evidence"], styles, arabic=ar)
    for item in analysis.get("evidence_trace") or []:
        story.append(_para(f"<b>{_text(item.get('clause'))}</b> — {_text(item.get('source'))} — {_text(item.get('keyword'))}", styles["Small"], arabic=ar, markup=True))
        story.append(_para(_text(item.get("text")), styles["Quote"], arabic=False))
        story.append(Spacer(1, 0.06 * inch))

    _section(story, labels["final_disclaimer"], styles, arabic=ar)
    final_text = "هذا التقرير مراجعة مدعومة بالذكاء الاصطناعي وليس رأيًا قانونيًا نهائيًا. يجب مراجعته من قبل مختص قبل الاعتماد عليه." if ar else "AI-assisted review only. This report is not legal advice and should not be treated as approval to sign. Have a qualified human reviewer confirm legal, financial, operational, and business implications before relying on it."
    story.append(_para(final_text, styles["Body"], arabic=ar))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
