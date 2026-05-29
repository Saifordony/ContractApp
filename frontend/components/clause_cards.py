from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from frontend.components.badges import status_badge
from frontend.services.formatters import titleize_key

WHY_MATTERS = {
    "parties": "Identifies who is legally bound by the contract.",
    "compensation": "Controls pay, currency, timing, and related financial expectations.",
    "termination": "Explains how the relationship can end and what notice is required.",
    "leave_policy": "Clarifies vacation, sick leave, holidays, and absence rules.",
    "governing_law": "Tells users which legal system applies to the contract.",
    "dispute_resolution": "Explains how disagreements are handled.",
    "confidentiality": "Protects sensitive business or personal information.",
}


def render_clause_card(clause_key: str, payload: Dict[str, Any], explanation: str | None = None) -> None:
    title = titleize_key(clause_key)
    status = payload.get("status", "unknown") if isinstance(payload, dict) else "unknown"
    confidence = payload.get("confidence", 0) if isinstance(payload, dict) else 0
    with st.expander(f"{title} · {status.replace('_', ' ').title()}", expanded=status == "found"):
        st.markdown(status_badge(status), unsafe_allow_html=True)
        st.caption(f"Confidence: {confidence}")
        st.markdown("**Plain-English summary**")
        if explanation and status == "found":
            st.success(str(explanation))
        elif status in {"not_found", "missing"}:
            st.info("No reliable evidence was found for this clause in the contract.")
        else:
            st.info("The app found possible evidence, but it may be incomplete or unclear.")
        st.markdown("**Why it matters**")
        st.write(WHY_MATTERS.get(clause_key, "This clause can affect contract rights, obligations, risk, or enforceability."))
        st.markdown("**Extracted text**")
        text = payload.get("extracted_text") if isinstance(payload, dict) else None
        if text:
            st.info(str(text))
        else:
            st.warning("No reliable evidence found.")
        issues = payload.get("issues", []) if isinstance(payload, dict) else []
        if issues:
            st.markdown("**Issues**")
            for issue in issues:
                st.write(f"- {issue}")
        action = payload.get("recommended_action") if isinstance(payload, dict) else None
        if action:
            st.markdown("**Recommended action**")
            st.write(action)
        evidence = payload.get("evidence_snippets", []) if isinstance(payload, dict) else []
        if evidence:
            with st.expander("Evidence snippets"):
                for ev in evidence:
                    st.info(ev.get("quote", ""))
                    if ev.get("location"):
                        st.caption(ev.get("location"))
