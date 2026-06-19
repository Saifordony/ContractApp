from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BRAND_PRIMARY = colors.HexColor("#172554")
BRAND_ACCENT = colors.HexColor("#2563EB")
BRAND_MUTED = colors.HexColor("#64748B")
BRAND_BORDER = colors.HexColor("#E2E8F0")
BRAND_BG = colors.HexColor("#F8FAFC")
BRAND_SUCCESS = colors.HexColor("#16A34A")
BRAND_WARNING = colors.HexColor("#D97706")
BRAND_DANGER = colors.HexColor("#DC2626")

REPORT_LABELS = {
    "english": {
        "tagline": "Simple-English AI contract review for business users",
        "client_name": "Client name",
        "contract_name": "Contract name",
        "date_generated": "Date generated",
        "important_note": "Important note",
        "not_legal_advice": "AI-assisted review only — not legal advice. Use this report to guide review, not as a final legal opinion.",
        "footer_note": "AI-assisted review only — not legal advice.",
        "executive_summary": "Executive Summary",
        "recommended_actions": "Recommended Actions",
        "contract_health": "Contract Health",
        "benchmark": "Benchmark Comparison",
        "key_terms": "Key Extracted Terms",
        "risks": "Main Risks",
        "appendix": "Appendix: Evidence Snippets",
        "health_chart": "Chart: Contract Health score by dimension",
        "benchmark_chart": "Chart: Benchmark alignment by clause type",
        "risk_chart": "Chart: Risk severity breakdown",
        "confidence_chart": "Chart: Confidence levels by section",
        "completeness_chart": "Chart: Extracted clauses completeness",
    },
    "arabic": {
        "tagline": "مراجعة عقود بالذكاء الاصطناعي بلغة واضحة لمستخدمي الأعمال",
        "client_name": "اسم العميل",
        "contract_name": "اسم العقد",
        "date_generated": "تاريخ الإصدار",
        "important_note": "ملاحظة مهمة",
        "not_legal_advice": "مراجعة بمساعدة الذكاء الاصطناعي فقط — هذا ليس رأياً قانونياً نهائياً.",
        "footer_note": "مراجعة بمساعدة الذكاء الاصطناعي فقط — ليست نصيحة قانونية.",
        "executive_summary": "الملخص التنفيذي",
        "recommended_actions": "التوصيات",
        "contract_health": "صحة العقد",
        "benchmark": "المقارنة المعيارية",
        "key_terms": "البنود الرئيسية",
        "risks": "المخاطر",
        "appendix": "ملحق الأدلة",
        "health_chart": "Chart: صحة العقد حسب البعد",
        "benchmark_chart": "Chart: توافق البنود مع المقارنة المعيارية",
        "risk_chart": "Chart: توزيع شدة المخاطر",
        "confidence_chart": "Chart: مستويات الثقة حسب القسم",
        "completeness_chart": "Chart: اكتمال البنود المستخرجة",
    },
}


def _report_language(language: str | None) -> str:
    lang = (language or "english").strip().lower()
    return "arabic" if lang in {"arabic", "ar", "ara", "العربية"} else "english"


def _label(key: str, language: str) -> str:
    return REPORT_LABELS[_report_language(language)].get(key, REPORT_LABELS["english"].get(key, key))


def titleize_key(value: Any) -> str:
    text = str(value or "").strip().replace("_", " ")
    return re.sub(r"\s+", " ", text).title() or "Not specified"


def simplify_text(value: Any, *, fallback: str = "Not available.", max_chars: int = 480) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return fallback
    replacements = {
        "indemnification": "covering losses",
        "asymmetric exposure": "one-sided risk",
        "jurisdiction": "court or legal location",
        "governing law": "the law that applies",
        "liability": "responsibility for losses",
    }
    lowered = text
    for legal, plain in replacements.items():
        lowered = re.sub(legal, plain, lowered, flags=re.IGNORECASE)
    if len(lowered) > max_chars:
        lowered = lowered[: max_chars - 3].rstrip() + "..."
    return lowered


def confidence_label(value: Any) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"high", "medium", "low"}:
            return normalized.title()
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "Medium"
    if score >= 0.75:
        return "High"
    if score >= 0.4:
        return "Medium"
    return "Low"


def _status_label(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status", "found")).replace("_", " ").title()
    if status == "Found":
        return "Complete"
    if status in {"Not Found", "Missing"}:
        return "Missing"
    return status or "Needs Review"


def _extract_clauses(report_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    structured = report_payload.get("structured_clauses", {})
    clauses = structured.get("clauses", {}) if isinstance(structured, dict) else {}
    if isinstance(clauses, dict) and clauses:
        return {str(k): v if isinstance(v, dict) else {"status": "found", "extracted_text": str(v)} for k, v in clauses.items()}

    raw_clauses = report_payload.get("clauses", {})
    if isinstance(raw_clauses, dict):
        return {
            str(k): {
                "status": "found" if str(v).strip() else "not_found",
                "extracted_text": str(v).strip() if str(v).strip() else None,
                "evidence_snippets": [{"quote": str(v).strip(), "location": "Extracted clause"}] if str(v).strip() else [],
                "confidence": 0.7 if str(v).strip() else 0.0,
            }
            for k, v in raw_clauses.items()
        }
    return {}


def _extract_evidence(clause_key: str, payload: Dict[str, Any]) -> List[Dict[str, str]]:
    snippets = payload.get("evidence_snippets") or []
    evidence: List[Dict[str, str]] = []
    if isinstance(snippets, list):
        for item in snippets[:3]:
            if isinstance(item, dict) and item.get("quote"):
                evidence.append({
                    "clause": titleize_key(clause_key),
                    "quote": simplify_text(item.get("quote"), max_chars=360),
                    "location": str(item.get("location") or "Contract evidence"),
                })
    text = payload.get("extracted_text")
    if text and not evidence:
        evidence.append({"clause": titleize_key(clause_key), "quote": simplify_text(text, max_chars=360), "location": "Extracted clause"})
    return evidence


def _risk_counts(health: Dict[str, Any]) -> Dict[str, int]:
    counts = {"High risk": 0, "Medium risk": 0, "Low risk": 0}
    risk_level = str(health.get("risk_level", "")).lower()
    if risk_level == "high":
        counts["High risk"] += 1
    elif risk_level == "medium":
        counts["Medium risk"] += 1
    elif risk_level == "low":
        counts["Low risk"] += 1
    for item in health.get("red_flags", []) or health.get("issues", []) or []:
        text = str(item).lower()
        if "high" in text or "critical" in text:
            counts["High risk"] += 1
        elif "low" in text:
            counts["Low risk"] += 1
        else:
            counts["Medium risk"] += 1
    return counts


def _completeness_counts(clauses: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    counts = {"Complete": 0, "Needs review": 0, "Missing": 0}
    for payload in clauses.values():
        status = str(payload.get("status", "found")).lower()
        if status == "found":
            counts["Complete"] += 1
        elif status in {"not_found", "missing"}:
            counts["Missing"] += 1
        else:
            counts["Needs review"] += 1
    return counts


def _benchmark_counts(benchmark: Dict[str, Any]) -> Dict[str, int]:
    counts = {"Aligned": 0, "Slightly different": 0, "Outlier": 0, "Not enough data": 0}
    rows = benchmark.get("your_contract_vs_benchmark", []) if isinstance(benchmark, dict) else []
    for row in rows:
        result = str(row.get("result", "")).lower() if isinstance(row, dict) else ""
        if "aligned" in result and "partial" not in result:
            counts["Aligned"] += 1
        elif "partial" in result or "slightly" in result:
            counts["Slightly different"] += 1
        elif "not found" in result or "below" in result or "missing" in result:
            counts["Outlier"] += 1
        else:
            counts["Not enough data"] += 1
    return counts


def _confidence_counts(clauses: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    counts = {"High": 0, "Medium": 0, "Low": 0}
    for payload in clauses.values():
        counts[confidence_label(payload.get("confidence"))] += 1
    return counts


class _PdfReport:
    def __init__(self, *, contract_title: str, client_name: str, report_title: str, language: str = "english"):
        self.buffer = io.BytesIO()
        self.canvas = canvas.Canvas(self.buffer, pagesize=A4, pageCompression=0)
        self.width, self.height = A4
        self.margin = 42
        self.y = self.height - 48
        self.page_number = 1
        self.contract_title = contract_title
        self.client_name = client_name
        self.report_title = report_title
        self.language = _report_language(language)
        self.body_font = "Helvetica"
        self.bold_font = "Helvetica-Bold"
        font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        bold_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSans", str(font_path)))
            self.body_font = "DejaVuSans"
        if bold_path.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(bold_path)))
            self.bold_font = "DejaVuSans-Bold"

    def save(self) -> bytes:
        self._footer()
        self.canvas.save()
        self.buffer.seek(0)
        return self.buffer.read()

    def _footer(self) -> None:
        c = self.canvas
        c.setStrokeColor(BRAND_BORDER)
        c.line(self.margin, 32, self.width - self.margin, 32)
        c.setFillColor(BRAND_MUTED)
        c.setFont(self.body_font, 8)
        c.drawString(self.margin, 20, _label("footer_note", self.language))
        c.drawRightString(self.width - self.margin, 20, f"Page {self.page_number}")

    def _new_page(self) -> None:
        self._footer()
        self.canvas.showPage()
        self.page_number += 1
        self.y = self.height - 48
        self._header()

    def ensure(self, needed: int = 70) -> None:
        if self.y < needed:
            self._new_page()

    def _header(self) -> None:
        c = self.canvas
        c.setFillColor(BRAND_PRIMARY)
        c.circle(self.margin + 9, self.height - 32, 9, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(self.bold_font, 9)
        c.drawCentredString(self.margin + 9, self.height - 35, "CI")
        c.setFillColor(BRAND_PRIMARY)
        c.setFont(self.bold_font, 11)
        c.drawString(self.margin + 24, self.height - 35, "Contract Intelligence")
        c.setFillColor(BRAND_MUTED)
        c.setFont(self.body_font, 8)
        c.drawRightString(self.width - self.margin, self.height - 35, self.contract_title[:60])

    def cover(self) -> None:
        c = self.canvas
        c.setFillColor(BRAND_BG)
        c.rect(0, 0, self.width, self.height, stroke=0, fill=1)
        c.setFillColor(BRAND_PRIMARY)
        c.circle(self.margin + 18, self.height - 92, 18, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(self.bold_font, 14)
        c.drawCentredString(self.margin + 18, self.height - 97, "CI")
        c.setFillColor(BRAND_PRIMARY)
        c.setFont(self.bold_font, 18)
        c.drawString(self.margin + 46, self.height - 98, "Contract Intelligence")
        c.setFont(self.bold_font, 28)
        c.drawString(self.margin, self.height - 180, self.report_title)
        c.setFillColor(BRAND_MUTED)
        c.setFont(self.body_font, 13)
        c.drawString(self.margin, self.height - 210, _label("tagline", self.language))
        self.y = self.height - 275
        self.card(_label("client_name", self.language), self.client_name or "Not specified")
        self.card(_label("contract_name", self.language), self.contract_title or "Not specified")
        self.card(_label("date_generated", self.language), datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
        self.card(_label("important_note", self.language), _label("not_legal_advice", self.language))
        self._new_page()

    def card(self, title: str, body: str, *, score_color=BRAND_ACCENT) -> None:
        self.ensure(90)
        c = self.canvas
        box_h = 56
        c.setFillColor(colors.white)
        c.setStrokeColor(BRAND_BORDER)
        c.roundRect(self.margin, self.y - box_h + 8, self.width - self.margin * 2, box_h, 8, stroke=1, fill=1)
        c.setFillColor(score_color)
        c.roundRect(self.margin, self.y - box_h + 8, 5, box_h, 2, stroke=0, fill=1)
        c.setFillColor(BRAND_PRIMARY)
        c.setFont(self.bold_font, 10)
        c.drawString(self.margin + 16, self.y - 14, title)
        c.setFillColor(colors.black)
        c.setFont(self.body_font, 9)
        self._draw_wrapped(body, self.margin + 16, self.y - 30, self.width - self.margin * 2 - 28, 11)
        self.y -= box_h + 8

    def section(self, title: str, subtitle: str = "") -> None:
        self.ensure(86)
        c = self.canvas
        c.setFillColor(BRAND_PRIMARY)
        c.setFont(self.bold_font, 15)
        c.drawString(self.margin, self.y, title)
        self.y -= 16
        if subtitle:
            c.setFillColor(BRAND_MUTED)
            c.setFont(self.body_font, 9)
            self._draw_wrapped(subtitle, self.margin, self.y, self.width - self.margin * 2, 11)
            self.y -= 10
        c.setStrokeColor(BRAND_BORDER)
        c.line(self.margin, self.y, self.width - self.margin, self.y)
        self.y -= 18

    def paragraph(self, text: str, *, size: int = 9, indent: int = 0, color=colors.black) -> None:
        self.ensure(60)
        self.canvas.setFillColor(color)
        self.canvas.setFont(self.body_font, size)
        used = self._draw_wrapped(simplify_text(text, max_chars=1200), self.margin + indent, self.y, self.width - self.margin * 2 - indent, size + 3)
        self.y -= used + 8

    def bullet_list(self, items: Iterable[Any], *, limit: int = 8) -> None:
        for item in list(items or [])[:limit]:
            self.paragraph(f"• {simplify_text(item, max_chars=280)}", indent=10)

    def table(self, headers: List[str], rows: List[List[str]], *, col_widths: List[int] | None = None) -> None:
        if not rows:
            self.paragraph("No data available.", color=BRAND_MUTED)
            return
        col_widths = col_widths or [int((self.width - self.margin * 2) / len(headers))] * len(headers)
        row_h = 48
        self.ensure(row_h + 40)
        c = self.canvas
        x = self.margin
        c.setFillColor(BRAND_PRIMARY)
        c.roundRect(x, self.y - 18, sum(col_widths), 22, 4, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(self.bold_font, 8)
        for idx, header in enumerate(headers):
            c.drawString(x + 5, self.y - 10, header)
            x += col_widths[idx]
        self.y -= 24
        for row in rows:
            self.ensure(row_h + 42)
            x = self.margin
            c.setStrokeColor(BRAND_BORDER)
            c.setFillColor(colors.white)
            c.rect(x, self.y - row_h + 8, sum(col_widths), row_h, stroke=1, fill=1)
            c.setFillColor(colors.black)
            c.setFont(self.body_font, 7.5)
            for idx, cell in enumerate(row):
                self._draw_wrapped(simplify_text(cell, max_chars=180), x + 5, self.y - 6, col_widths[idx] - 10, 9, max_lines=4)
                x += col_widths[idx]
            self.y -= row_h
        self.y -= 8

    def bar_chart(self, title: str, values: Dict[str, int | float], *, max_value: float | None = None) -> None:
        self.ensure(130)
        c = self.canvas
        c.setFillColor(BRAND_PRIMARY)
        c.setFont(self.bold_font, 10)
        c.drawString(self.margin, self.y, title)
        self.y -= 18
        max_value = max_value or max([float(v) for v in values.values()] + [1.0])
        colors_for_bars = [BRAND_ACCENT, BRAND_SUCCESS, BRAND_WARNING, BRAND_DANGER, BRAND_MUTED]
        for idx, (label, value) in enumerate(values.items()):
            self.ensure(28)
            v = float(value or 0)
            c.setFillColor(BRAND_MUTED)
            c.setFont(self.body_font, 8)
            c.drawString(self.margin, self.y, str(label)[:28])
            bar_x = self.margin + 135
            bar_w = min(250, int(250 * (v / max_value))) if max_value else 0
            c.setFillColor(colors.HexColor("#E5E7EB"))
            c.roundRect(bar_x, self.y - 2, 250, 9, 3, stroke=0, fill=1)
            c.setFillColor(colors_for_bars[idx % len(colors_for_bars)])
            c.roundRect(bar_x, self.y - 2, max(2, bar_w), 9, 3, stroke=0, fill=1)
            c.setFillColor(BRAND_PRIMARY)
            c.drawRightString(self.width - self.margin, self.y, str(int(v) if v.is_integer() else round(v, 1)))
            self.y -= 20
        self.y -= 8

    def _draw_wrapped(self, text: str, x: float, y: float, width: float, line_height: float, max_lines: int | None = None) -> float:
        words = str(text or "").split()
        line = ""
        lines: List[str] = []
        max_chars = max(20, int(width / 4.5))
        for word in words:
            candidate = f"{line} {word}".strip()
            if len(candidate) > max_chars and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        if not lines:
            lines = [""]
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1][: max(0, len(lines[-1]) - 3)] + "..."
        for idx, line_text in enumerate(lines):
            self.ensure(50)
            self.canvas.drawString(x, y - (idx * line_height), line_text)
        return len(lines) * line_height


def build_professional_report_pdf(
    contract_title: str,
    report_payload: Dict[str, Any],
    *,
    client_name: str = "Not specified",
    report_title: str = "Contract Review Report",
    language: str = "english",
) -> bytes:
    payload = report_payload or {}
    health = payload.get("health_evaluation", payload if isinstance(payload, dict) else {})
    benchmark = payload.get("benchmark_result") or payload.get("benchmark") or {}
    clauses = _extract_clauses(payload)
    dimensions = health.get("dimensions", []) if isinstance(health, dict) else []

    language = _report_language(language)
    pdf = _PdfReport(contract_title=contract_title, client_name=client_name, report_title=report_title, language=language)
    pdf.cover()

    score = health.get("health_score", "N/A") if isinstance(health, dict) else "N/A"
    benchmark_score = "N/A"
    if isinstance(benchmark, dict):
        benchmark_score = benchmark.get("overall_position", {}).get("alignment_score", benchmark.get("overall_score", "N/A"))
    risk = titleize_key(health.get("risk_level", "Not available")) if isinstance(health, dict) else "Not available"

    pdf.section(_label("executive_summary", language), "A short, simple-English view of what matters most.")
    pdf.card("Contract health score", f"{score}/100 — Risk level: {risk}", score_color=BRAND_ACCENT)
    pdf.card("Benchmark alignment score", f"{benchmark_score}/100. If no benchmark is available, run Benchmark Comparison first.", score_color=BRAND_SUCCESS)
    summary = health.get("reasoning") or health.get("executive_summary") or "This report highlights completeness, risk, benchmark alignment, and recommended next steps."
    pdf.paragraph(summary)

    missing = health.get("missing_critical_clauses", []) if isinstance(health, dict) else []
    changes = health.get("required_changes", []) if isinstance(health, dict) else []
    pdf.section(_label("recommended_actions", language), "Practical next steps before approval or signing.")
    if changes or missing:
        pdf.bullet_list(changes or [f"Add or clarify: {titleize_key(item)}" for item in missing], limit=10)
    else:
        pdf.paragraph("No critical recommended actions were found in the available analysis. Still review the evidence before signing.")

    pdf.section(_label("contract_health", language), "How complete, balanced, and manageable the contract appears.")
    if dimensions:
        rows = []
        chart_values: Dict[str, int] = {}
        for item in dimensions[:8]:
            name = titleize_key(item.get("name"))
            dim_score = int(item.get("score", 0) or 0)
            chart_values[name] = dim_score
            rows.append([
                name,
                f"{dim_score}/100",
                simplify_text(item.get("reason") or item.get("explanation"), max_chars=180),
                simplify_text(item.get("recommended_action"), max_chars=160),
            ])
        pdf.bar_chart(_label("health_chart", language), chart_values, max_value=100)
        pdf.table(["Dimension", "Score", "Simple explanation", "Recommended action"], rows, col_widths=[105, 55, 175, 175])
    else:
        pdf.paragraph("No dimension-level health data was available. Run Contract Health for a fuller review.")

    pdf.section(_label("benchmark", language), "Benchmark is separate from Contract Health. It compares clauses against expected standards or peer data when available.")
    if isinstance(benchmark, dict) and benchmark:
        context = benchmark.get("benchmark_context", {})
        pdf.paragraph(f"Benchmark basis: {context.get('benchmark_basis', 'Not specified')}. Peer group size: {context.get('sample_size') or 'Not available'}.")
        rows = []
        for row in benchmark.get("your_contract_vs_benchmark", [])[:8]:
            rows.append([
                row.get("review_area", "Area"),
                row.get("your_contract", "Not found"),
                row.get("result", "Not enough benchmark data"),
                row.get("recommendation", "Review this area."),
            ])
        pdf.bar_chart(_label("benchmark_chart", language), _benchmark_counts(benchmark))
        pdf.table(["Clause", "Your clause summary", "Benchmark result", "Suggested improvement"], rows, col_widths=[95, 180, 105, 130])
    else:
        pdf.paragraph("Benchmark data was not available in this report. Run Benchmark Comparison to add alignment results.")
        pdf.bar_chart(_label("benchmark_chart", language), {"Aligned": 0, "Outlier": 0, "Not enough data": 1})

    pdf.section(_label("key_terms", language), "What was found, why it matters, confidence, and evidence.")
    completeness = _completeness_counts(clauses)
    confidence = _confidence_counts(clauses)
    pdf.bar_chart(_label("completeness_chart", language), completeness)
    pdf.bar_chart(_label("confidence_chart", language), confidence)
    rows = []
    evidence_rows: List[Tuple[str, str, str]] = []
    for key, clause in list(clauses.items())[:14]:
        evidence = _extract_evidence(key, clause)
        for ev in evidence[:2]:
            evidence_rows.append((ev["clause"], ev["quote"], ev["location"]))
        found = clause.get("extracted_text") or "No reliable evidence found."
        why = clause.get("why_it_matters") or clause.get("recommended_action") or "This helps users understand rights, duties, timing, or risk."
        rows.append([
            titleize_key(key),
            _status_label(clause),
            simplify_text(found, max_chars=160),
            simplify_text(why, max_chars=130),
            confidence_label(clause.get("confidence")),
        ])
    pdf.table(["Clause", "Status", "What was found", "Why it matters", "Confidence"], rows, col_widths=[80, 65, 190, 145, 70])

    pdf.section(_label("risks", language), "Simple risk view based on the available health analysis.")
    pdf.bar_chart(_label("risk_chart", language), _risk_counts(health if isinstance(health, dict) else {}))
    issues = health.get("issues", []) if isinstance(health, dict) else []
    red_flags = health.get("red_flags", []) if isinstance(health, dict) else []
    risks = issues or red_flags or []
    if risks:
        pdf.bullet_list(risks, limit=10)
    else:
        pdf.paragraph("No specific risk list was available. Review missing clauses, health dimensions, and benchmark gaps.")

    pdf.section(_label("appendix", language), "Short source quotes used in this report.")
    if evidence_rows:
        rows = [[clause, quote, location] for clause, quote, location in evidence_rows[:18]]
        pdf.table(["Section", "Evidence from contract", "Location"], rows, col_widths=[100, 330, 80])
    else:
        pdf.paragraph("No evidence snippets were available. Run clause extraction before exporting the report.")

    return pdf.save()
