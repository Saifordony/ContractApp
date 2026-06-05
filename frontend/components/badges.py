from __future__ import annotations

import streamlit as st

from frontend.services.formatters import status_label


def badge(label: str, tone: str = "neutral") -> str:
    return f"<span class='badge badge-{tone}'>{label}</span>"


def status_badge(status: str | None) -> str:
    label = status_label(status)
    lower = str(status or "").lower()
    tone = "neutral"
    if lower == "found":
        tone = "success"
    elif lower in {"partial", "partially_found"}:
        tone = "warning"
    elif lower == "needs_review":
        tone = "orange"
    elif lower in {"not_found", "missing"}:
        tone = "danger"
    return badge(label, tone)


def render_status_badge(status: str | None) -> None:
    st.markdown(status_badge(status), unsafe_allow_html=True)
