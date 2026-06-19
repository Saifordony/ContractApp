"""Horizontal severity-distribution bar for found / partial / missing clauses."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import streamlit as st

_SUCCESS = "#22D68F"
_WARNING = "#F59E0B"
_DANGER = "#EF4444"
_MUTED = "#6B7A99"


def _count_statuses(clauses: Dict[str, Any]) -> Tuple[int, int, int]:
    """Count found / partial / missing statuses from a clause dict."""
    found = partial = missing = 0
    for payload in (clauses or {}).values():
        status = ""
        if isinstance(payload, dict):
            status = str(payload.get("status", "")).lower()
        else:
            status = str(payload).lower()
        if status in {"found", "present", "ok"}:
            found += 1
        elif status in {"partial", "partially_found", "needs_review", "low_confidence"}:
            partial += 1
        elif status in {"missing", "not_found", "absent"}:
            missing += 1
    return found, partial, missing


def risk_heatmap_html(clauses: Dict[str, Any]) -> str:
    """Build the color-coded distribution bar HTML for a clause dict."""
    found, partial, missing = _count_statuses(clauses)
    total = found + partial + missing
    if total == 0:
        return (
            f"<div style=\"color:{_MUTED};font-family:'DM Sans',sans-serif;"
            f"font-size:0.85rem;\">No clause status data available.</div>"
        )

    def _pct(n: int) -> float:
        return round(100 * n / total, 2)

    segments = [
        (found, _SUCCESS),
        (partial, _WARNING),
        (missing, _DANGER),
    ]
    bar = "".join(
        f"<div style='width:{_pct(count)}%;background:{color};height:100%;'></div>"
        for count, color in segments
        if count > 0
    )
    legend = (
        f"<span style='color:{_SUCCESS};'>{found} found</span> · "
        f"<span style='color:{_WARNING};'>{partial} partial</span> · "
        f"<span style='color:{_DANGER};'>{missing} missing</span>"
    )
    return (
        "<div class='risk-heatmap' style='margin:0.5rem 0;'>"
        "<div style='display:flex;height:14px;border-radius:999px;overflow:hidden;"
        f"background:rgba(107,122,153,0.2);'>{bar}</div>"
        f"<div style=\"font-family:'DM Sans',sans-serif;font-size:0.8rem;"
        f"margin-top:0.4rem;\">{legend}</div>"
        "</div>"
    )


def risk_heatmap(clauses: Dict[str, Any]) -> None:
    """Render the distribution of found/partial/missing clauses as a color bar."""
    st.markdown(risk_heatmap_html(clauses), unsafe_allow_html=True)
