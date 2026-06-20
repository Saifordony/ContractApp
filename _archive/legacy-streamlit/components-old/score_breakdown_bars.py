"""Horizontal progress bars visualising a contract-health score breakdown."""

from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

_SUCCESS = "#22D68F"
_WARNING = "#F59E0B"
_DANGER = "#EF4444"
_PRIMARY = "#D4E2FF"
_MUTED = "#6B7A99"

# Bar width and colour by severity.
_SEVERITY_WIDTH = {"high": 80, "medium": 50, "low": 25}
_SEVERITY_COLOR = {"high": _DANGER, "medium": _WARNING, "low": _SUCCESS}


def _severity(item: Dict[str, Any]) -> str:
    return str(item.get("severity", "medium")).strip().lower()


def score_breakdown_bar_html(item: Dict[str, Any]) -> str:
    """Build the labelled horizontal bar HTML for one breakdown area."""
    severity = _severity(item)
    width = _SEVERITY_WIDTH.get(severity, 50)
    color = _SEVERITY_COLOR.get(severity, _WARNING)
    area = str(item.get("area", "Area"))
    impact = str(item.get("impact", "")).strip()
    impact_html = (
        f"<span style='color:{_MUTED};font-size:0.78rem;'>{impact}</span>" if impact else ""
    )
    return (
        "<div class='score-breakdown-bar' style='margin:0.4rem 0;'>"
        "<div style='display:flex;justify-content:space-between;align-items:baseline;'>"
        f"<span style=\"font-family:'DM Sans',sans-serif;color:{_PRIMARY};"
        f"font-size:0.85rem;\">{area}</span>{impact_html}</div>"
        "<div style='height:10px;border-radius:999px;background:rgba(107,122,153,0.2);"
        "overflow:hidden;margin-top:0.25rem;'>"
        f"<div style='width:{width}%;height:100%;background:{color};'></div>"
        "</div></div>"
    )


def score_breakdown_bars(breakdown: List[Dict[str, Any]]) -> None:
    """Render health-score breakdown areas as labelled horizontal bars.

    Each item: ``{"area", "impact", "severity", "explanation"}``.  Bar width is
    proportional to severity (high=80%, medium=50%, low=25%) and coloured
    high=danger, medium=warning, low=success.  An expander per bar reveals the
    explanation text.
    """
    for item in breakdown or []:
        if not isinstance(item, dict):
            continue
        st.markdown(score_breakdown_bar_html(item), unsafe_allow_html=True)
        explanation = str(item.get("explanation", "")).strip()
        if explanation:
            with st.expander(f"Why: {item.get('area', 'this area')}"):
                st.write(explanation)
