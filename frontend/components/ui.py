"""Small shared HTML helpers for the redesigned pages."""

from __future__ import annotations

import streamlit as st


def stat_card_html(label: str, value: str, sub: str = "") -> str:
    sub_html = f"<div class='stat-label'>{sub}</div>" if sub else ""
    return (
        "<div class='stat-card'>"
        f"<div class='stat-label'>{label}</div>"
        f"<div class='stat-value'>{value}</div>"
        f"{sub_html}</div>"
    )


def stat_card(label: str, value: str, sub: str = "") -> None:
    st.markdown(stat_card_html(label, value, sub), unsafe_allow_html=True)


def confidence_badge_html(confidence: float) -> str:
    """Render a confidence pill from a 0-1 score."""
    try:
        score = float(confidence)
    except (TypeError, ValueError):
        score = 0.0
    if score >= 0.7:
        cls, label = "confidence-high", "High confidence"
    elif score >= 0.4:
        cls, label = "confidence-medium", "Medium confidence"
    else:
        cls, label = "confidence-low", "Low confidence"
    return f"<span class='confidence-badge {cls}'>{label} · {int(round(score * 100))}%</span>"


def confidence_badge(confidence: float) -> None:
    st.markdown(confidence_badge_html(confidence), unsafe_allow_html=True)


def demo_banner() -> None:
    st.info("🎭 Demo Mode — you are viewing sample data, not a real analysis.")
