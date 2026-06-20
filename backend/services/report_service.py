"""PDF report generation for contract analysis results."""
from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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


def _para(text: Any, style: ParagraphStyle) -> Paragraph:
    clean = _text(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(clean, style)


def _section(story: list, title: str, styles) -> None:
    story.append(Spacer(1, 0.18 * inch))
    story.append(Paragraph(title, styles["SectionTitle"]))
    story.append(Spacer(1, 0.08 * inch))


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(0.55 * inch, 0.38 * inch, "AI-assisted review only — not legal advice.")
    canvas.drawRightString(A4[0] - 0.55 * inch, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def generate_analysis_pdf(contract: dict[str, Any], analysis: dict[str, Any], generated_at: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.55 * inch, leftMargin=0.55 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch)
    base = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle("ReportTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24, leading=30, textColor=colors.HexColor("#0f172a"), spaceAfter=14),
        "Subtitle": ParagraphStyle("ReportSubtitle", parent=base["BodyText"], fontSize=10, leading=15, textColor=colors.HexColor("#475569")),
        "SectionTitle": ParagraphStyle("SectionTitle", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=colors.HexColor("#1d4ed8")),
        "Body": ParagraphStyle("ReportBody", parent=base["BodyText"], fontSize=9.5, leading=14, textColor=colors.HexColor("#0f172a")),
        "Small": ParagraphStyle("ReportSmall", parent=base["BodyText"], fontSize=8, leading=11, textColor=colors.HexColor("#475569")),
        "Quote": ParagraphStyle("EvidenceQuote", parent=base["BodyText"], fontSize=8.4, leading=12, leftIndent=10, borderColor=colors.HexColor("#bfdbfe"), borderWidth=1, borderPadding=6, backColor=colors.HexColor("#eff6ff")),
    }
    story: list[Any] = []
    contract_name = _text(contract.get("name") or contract.get("filename"), "Untitled contract")
    story.append(Paragraph("Contract Intelligence Report", styles["Title"]))
    story.append(Paragraph(contract_name, styles["SectionTitle"]))
    story.append(Paragraph(f"Date generated: {generated_at}", styles["Subtitle"]))
    story.append(Paragraph(f"AI mode: {_text(analysis.get('source'))} | LLM used: {_text(analysis.get('llm_used'))} | Model: {_text(analysis.get('active_model'))}", styles["Subtitle"]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("Disclaimer: This report is an AI-assisted contract review and is not final legal advice. Human legal and business review is required before relying on it.", styles["Quote"]))
    story.append(PageBreak())

    _section(story, "1. Executive Summary", styles)
    summary_rows = [
        ["Overall health", f"{_text(analysis.get('health_score'))}/100"],
        ["Risk level", _text(analysis.get("risk_level"))],
        ["AI status", _text(analysis.get("ai_status"))],
    ]
    story.append(Table(summary_rows, colWidths=[1.8 * inch, 4.6 * inch], style=TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")), ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#cbd5e1")), ("INNERGRID", (0, 0), (-1, -1), .25, colors.HexColor("#e2e8f0")), ("VALIGN", (0, 0), (-1, -1), "TOP")])) )
    story.append(Spacer(1, 0.12 * inch))
    story.append(_para(analysis.get("executive_summary"), styles["Body"]))

    _section(story, "2. Key Terms Extracted", styles)
    key_terms = analysis.get("key_terms") or []
    if key_terms:
        for term in key_terms:
            story.append(Paragraph(f"<b>{_text(term.get('term'))}</b>: {_text(term.get('extracted_value'))}", styles["Body"]))
            story.append(Paragraph(f"Explanation: {_text(term.get('simple_explanation'))}", styles["Small"]))
            story.append(Paragraph(f"Verify: {_text(term.get('risk_or_verify'))}", styles["Small"]))
            story.append(Paragraph(f"Evidence: {_evidence_text(term.get('evidence'))}", styles["Quote"]))
            story.append(Spacer(1, 0.08 * inch))
    else:
        story.append(_para("No key terms were extracted. Run analysis again with a clearer contract scan if this appears incorrect.", styles["Body"]))

    _section(story, "3. Risk Overview", styles)
    risks = analysis.get("risks") or []
    if risks:
        for risk in risks:
            story.append(Paragraph(f"<b>{_text(risk.get('title'))}</b> — Severity: {_text(risk.get('severity'))}", styles["Body"]))
            story.append(Paragraph(f"Impact: {_text(risk.get('explanation'))}", styles["Small"]))
            story.append(Paragraph(f"Recommended action: {_text(risk.get('suggested_mitigation') or risk.get('recommendation'))}", styles["Small"]))
            story.append(Spacer(1, 0.06 * inch))
    else:
        story.append(_para("No major risks were detected from the extracted clauses.", styles["Body"]))

    _section(story, "4. Clause-by-Clause Review", styles)
    for clause in analysis.get("clauses") or []:
        story.append(Paragraph(f"<b>{_text(clause.get('title'))}</b> — {_text(clause.get('status'))} — Priority: {_text(clause.get('review_priority'))}", styles["Body"]))
        story.append(Paragraph(f"Evidence: {_evidence_text(clause.get('evidence'))}", styles["Quote"]))
        for label, key in [("Simple explanation", "simple_explanation"), ("Why it matters", "why_it_matters"), ("Risk in plain English", "risk_in_plain_english"), ("Recommendation", "ai_recommendation"), ("Negotiation note", "negotiation_note")]:
            story.append(Paragraph(f"<b>{label}:</b> {_text(clause.get(key))}", styles["Small"]))
        story.append(Spacer(1, 0.12 * inch))

    _section(story, "5. Missing / Weak Clauses", styles)
    missing = analysis.get("missing_critical_clauses") or analysis.get("missing_clauses") or []
    if missing:
        for item in missing:
            story.append(Paragraph(f"<b>{_text(item).replace('_', ' ').title()}</b>: Review whether this protection should be added or strengthened.", styles["Body"]))
    else:
        story.append(_para("No missing critical clauses were identified by the current analysis.", styles["Body"]))

    _section(story, "6. Recommended Actions", styles)
    actions = analysis.get("recommended_actions") or analysis.get("recommended_improvements") or []
    if actions:
        for action in actions:
            story.append(Paragraph(f"• {_text(action)}", styles["Body"]))
    else:
        story.append(_para("Confirm extracted business terms and complete human legal review before signature.", styles["Body"]))

    _section(story, "7. Evidence Appendix", styles)
    for item in analysis.get("evidence_trace") or []:
        story.append(Paragraph(f"<b>{_text(item.get('clause'))}</b> — {_text(item.get('source'))} — {_text(item.get('keyword'))}", styles["Small"]))
        story.append(Paragraph(_text(item.get("text")), styles["Quote"]))
        story.append(Spacer(1, 0.06 * inch))

    _section(story, "8. Disclaimer", styles)
    story.append(_para("AI-assisted review only. This report is not legal advice and should not be treated as approval to sign. Have a qualified human reviewer confirm legal, financial, operational, and business implications before relying on it.", styles["Body"]))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
