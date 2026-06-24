"""First-visit, dismissible onboarding stepper for new users."""

from __future__ import annotations

import streamlit as st

_ACCENT = "#4F7FEF"
_PRIMARY = "#D4E2FF"
_MUTED = "#6B7A99"
_CARD = "#131D30"
_SUBTLE = "#344263"

_STEPS = [
    ("⬆️", "Upload contract", "Add a PDF, DOCX, or paste text."),
    ("🤖", "Run AI analysis", "Extract clauses, risks, and a health score."),
    ("💬", "Chat with contract", "Ask questions and get evidence-backed answers."),
    ("📊", "Benchmark & report", "Compare to MENA market and export a report."),
]


def onboarding_banner_html() -> str:
    """Build the horizontal stepper HTML for the onboarding flow."""
    steps_html = ""
    for index, (icon, title, subtitle) in enumerate(_STEPS, start=1):
        steps_html += (
            "<div style='flex:1;min-width:140px;text-align:center;'>"
            f"<div style='font-size:1.4rem;'>{icon}</div>"
            f"<div style=\"font-family:'DM Sans',sans-serif;color:{_PRIMARY};"
            f"font-weight:600;font-size:0.9rem;margin-top:0.25rem;\">{index}. {title}</div>"
            f"<div style='color:{_MUTED};font-size:0.78rem;margin-top:0.15rem;'>{subtitle}</div>"
            "</div>"
        )
    return (
        f"<div class='onboarding-banner' style=\"background:{_CARD};"
        f"border:1px solid {_SUBTLE};border-left:4px solid {_ACCENT};"
        "border-radius:14px;padding:1rem 1.25rem;margin-bottom:1rem;'>"
        f"<div style=\"font-family:'Playfair Display',serif;color:{_PRIMARY};"
        "font-size:1.05rem;margin-bottom:0.75rem;\">Welcome — get started in 4 steps</div>"
        "<div style='display:flex;gap:0.5rem;flex-wrap:wrap;'>"
        f"{steps_html}</div></div>"
    )


def onboarding_banner() -> None:
    """Show a 4-step onboarding flow for first-time users.

    Renders only when ``st.session_state['onboarded']`` is not set.  A dismiss
    button sets the flag so the banner does not reappear.  Degrades gracefully
    if session state is unavailable.
    """
    try:
        already = bool(st.session_state.get("onboarded"))
    except Exception:
        already = False
    if already:
        return

    st.markdown(onboarding_banner_html(), unsafe_allow_html=True)
    if st.button("Got it — don't show this again", key="onboarding_dismiss"):
        st.session_state["onboarded"] = True
        # Re-run so the banner disappears immediately where supported.
        rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
        if callable(rerun):
            rerun()
