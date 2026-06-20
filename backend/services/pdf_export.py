"""Real PDF report generation (reportlab).

Produces an actual downloadable PDF of the analysis — never a stub. Registers a
Unicode font (DejaVu) when available so Arabic renders; with arabic-reshaper +
python-bidi present, Arabic is reshaped and bidi-ordered for correct display.
"""
from __future__ import annotations

import io
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.constants import CLAUSE_LABELS, HEALTH_DIMENSIONS

_FONT = "Helvetica"
_BOLD = "Helvetica-Bold"

_FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/freefont/FreeSans.ttf", "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
]


def _register_fonts() -> None:
    global _FONT, _BOLD
    for regular, bold in _FONT_CANDIDATES:
        if os.path.exists(regular):
            try:
                pdfmetrics.registerFont(TTFont("CAP", regular))
                pdfmetrics.registerFont(TTFont("CAP-Bold", bold if os.path.exists(bold) else regular))
                _FONT, _BOLD = "CAP", "CAP-Bold"
                return
            except Exception:
                continue


_register_fonts()

try:  # optional Arabic shaping
    import arabic_reshaper
    from bidi.algorithm import get_display

    _ARABIC_SHAPING = True
except Exception:  # pragma: no cover
    _ARABIC_SHAPING = False


def _shape(text: str) -> str:
    if not text:
        return ""
    if _ARABIC_SHAPING and any("؀" <= ch <= "ۿ" for ch in text):
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text
    return text


def _styles():
    base = getSampleStyleSheet()
    normal = ParagraphStyle("cap_normal", parent=base["Normal"], fontName=_FONT, fontSize=9, leading=12)
    title = ParagraphStyle("cap_title", parent=base["Title"], fontName=_BOLD, fontSize=18)
    h2 = ParagraphStyle("cap_h2", parent=base["Heading2"], fontName=_BOLD, fontSize=12)
    small = ParagraphStyle("cap_small", parent=normal, fontSize=8, textColor=colors.grey)
    return normal, title, h2, small


def build_analysis_pdf(contract: dict, analysis: dict, benchmark: dict | None = None) -> bytes:
    normal, title, h2, small = _styles()
    language = contract.get("language", "en")
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Contract Analysis Report",
                            leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    story: list = []

    story.append(Paragraph(_shape(contract.get("title", "Contract Analysis")), title))
    meta = f"{contract.get('contract_type', '')} · {contract.get('region', '')} · {language.upper()}"
    story.append(Paragraph(meta, small))
    story.append(Spacer(1, 6))

    if analysis.get("degraded"):
        story.append(Paragraph(
            "AI was unavailable — these results were produced by keyword matching and need human review.",
            ParagraphStyle("warn", parent=normal, textColor=colors.red)))
        story.append(Spacer(1, 6))

    # Health
    health = analysis.get("health", {})
    story.append(Paragraph("Health Score", h2))
    story.append(Paragraph(
        f"<b>{health.get('overall_score', 0)}/100</b> &nbsp; Grade {health.get('grade', '-')} &nbsp; "
        f"(confidence {round(health.get('confidence', 0) * 100)}%)", normal))
    dim_rows = [["Dimension", "Score", "Notes"]]
    dim_labels = {d["key"]: d["label"] for d in HEALTH_DIMENSIONS}
    for dim in health.get("dimensions", []):
        label = dim_labels.get(dim["key"], {}).get(language, dim["key"])
        dim_rows.append([_shape(label), str(dim.get("score", 0)), Paragraph(_shape(dim.get("explanation", "")), small)])
    dim_table = Table(dim_rows, colWidths=[35 * mm, 18 * mm, 110 * mm])
    dim_table.setStyle(_table_style())
    story.append(dim_table)
    story.append(Spacer(1, 10))

    # Clauses
    story.append(Paragraph("Clause Findings", h2))
    clause_rows = [["Clause", "Status", "Conf.", "Explanation & Evidence"]]
    for clause in analysis.get("clauses", []):
        label = CLAUSE_LABELS.get(clause["key"], {}).get(language, clause["key"])
        detail = _shape(clause.get("explanation", ""))
        if clause.get("evidence"):
            detail += f'<br/><i>“{_shape(clause["evidence"][0]["text"][:240])}”</i>'
        clause_rows.append([
            _shape(label), clause.get("status", ""), f"{round(clause.get('confidence', 0) * 100)}%",
            Paragraph(detail, small),
        ])
    clause_table = Table(clause_rows, colWidths=[30 * mm, 22 * mm, 14 * mm, 97 * mm])
    clause_table.setStyle(_table_style())
    story.append(clause_table)

    # Benchmark
    if benchmark:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Benchmark Comparison", h2))
        story.append(Paragraph(
            f"Score <b>{benchmark.get('overall_score', 0)}/100</b> · Grade {benchmark.get('grade', '-')}", normal))
        gap_rows = [["Clause", "Severity", "Recommendation"]]
        for gap in benchmark.get("gaps", []):
            gap_rows.append([gap.get("clause_key", ""), gap.get("severity", ""),
                             Paragraph(_shape(gap.get("recommendation", "")), small)])
        if len(gap_rows) > 1:
            gap_table = Table(gap_rows, colWidths=[35 * mm, 22 * mm, 106 * mm])
            gap_table.setStyle(_table_style())
            story.append(gap_table)

    doc.build(story)
    return buffer.getvalue()


def _table_style() -> TableStyle:
    return TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("FONTNAME", (0, 0), (-1, 0), _BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f57d6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
