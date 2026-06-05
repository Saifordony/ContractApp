from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from frontend.services.formatters import titleize_key


def render_readiness_review(evaluation: Dict[str, Any]) -> None:
    approved = bool(evaluation.get("approved"))
    score = int(evaluation.get("health_score", 0) or 0)
    risk = str(evaluation.get("risk_level", "medium")).title()
    result = "Ready For Approval" if approved else "Requires Review Before Approval"
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Readiness Score", f"{score}/100")
    c2.metric("Risk Level", risk)
    c3.metric("Overall Result", result)
    c4.metric("Contract Type", titleize_key(evaluation.get("contract_type")))
    st.progress(max(0, min(100, score)) / 100)
    st.markdown("### Executive Summary")
    st.info(evaluation.get("reasoning", "No executive summary available."))
    findings = []
    for item in evaluation.get("issues", []) or []:
        findings.append({"Area": "Key Review Finding", "Impact": "Needs attention", "Severity": risk, "Explanation": item})
    for item in evaluation.get("required_changes", []) or []:
        findings.append({"Area": "Recommended Next Step", "Impact": "Improves readiness", "Severity": "Medium", "Explanation": item})
    if findings:
        st.markdown("### Score Breakdown")
        st.dataframe(findings, use_container_width=True, hide_index=True)
    missing = evaluation.get("missing_critical_clauses", []) or []
    if missing:
        st.markdown("### Required Clauses Not Found")
        for item in missing:
            st.write(f"- Required Clause Not Found: {item}")
    recommended = evaluation.get("missing_recommended_clauses", []) or []
    if recommended:
        st.markdown("### Recommended Protections Not Found")
        for item in recommended:
            st.write(f"- Recommended Protection Not Found: {item}")
