"""Analysis page: upload / demo, tabbed results (overview, clauses, risk, chat, report)."""

from __future__ import annotations

import json

import streamlit as st

from frontend.auth import require_auth
from frontend.components.alerts import empty_state
from frontend.components.evidence_block import evidence_block
from frontend.components.health_ring import health_ring
from frontend.components.risk_heatmap import risk_heatmap
from frontend.components.score_breakdown_bars import score_breakdown_bars
from frontend.components.sidebar import api_base_url, render_app_sidebar
from frontend.components.ui import demo_banner
from frontend.demo_data import DEMO_ANALYSIS_RESULTS, DEMO_CONTRACT_TEXT, DEMO_SCORE_BREAKDOWN
from frontend.services.api_client import request_json
from frontend.styles.global_css import apply_global_css

try:
    from backend.services.contract_intelligence import clause_readability, detect_contract_language
except Exception:  # pragma: no cover - backend not importable in pure-frontend deploys
    clause_readability = None
    detect_contract_language = None

ALLOWED_EXT = {"pdf", "docx", "txt", "png", "jpg", "jpeg"}

st.set_page_config(page_title="Analysis · Contract Intelligence", page_icon="📄", layout="wide")
apply_global_css(theme_mode=st.session_state.get("theme_mode", "dark"))
require_auth()
render_app_sidebar()

st.markdown("<h1 class='display-heading'>Contract Analysis</h1>", unsafe_allow_html=True)

# --- Input: paste / upload / demo -------------------------------------------------
col_a, col_b = st.columns([3, 1])
with col_a:
    pasted = st.text_area("Paste contract text", value=st.session_state.get("contract_text", ""), height=160)
    uploaded = st.file_uploader("Or upload a file", type=sorted(ALLOWED_EXT))
with col_b:
    if st.button("🎭 Try Demo Contract", use_container_width=True):
        st.session_state["analysis_results"] = DEMO_ANALYSIS_RESULTS
        st.session_state["contract_text"] = DEMO_CONTRACT_TEXT
        st.session_state["is_demo"] = True
        st.toast("🎭 Demo workspace loaded", icon="🎭")

if st.button("Analyze contract", type="primary"):
    if uploaded is not None and uploaded.name.rsplit(".", 1)[-1].lower() not in ALLOWED_EXT:
        st.error("Only PDF, DOCX, TXT, PNG, and JPG files are supported.")
    elif uploaded is None and len(pasted.strip()) < 50:
        st.error("Contract text is too short to analyze meaningfully.")
    else:
        st.session_state["is_demo"] = False
        with st.spinner("Analyzing contract with Llama 3.1:8b..."):
            payload = {"contract_text": pasted, "response_language": st.session_state.get("ui_language", "english")}
            result = request_json(
                api_base_url(), "/genai/analyze-contract-text", method="POST",
                token=st.session_state.get("token"), data=payload, timeout=180,
            )
        if isinstance(result, dict) and result.get("error"):
            if result["error"] == "llm_unavailable":
                st.toast("⚠️ AI model unavailable — using keyword fallback", icon="⚠️")
            st.warning(result.get("message", "Analysis failed."))
        else:
            st.session_state["analysis_results"] = result
            st.session_state["contract_text"] = pasted
            st.toast("✅ Analysis complete", icon="✅")

results = st.session_state.get("analysis_results")
if not results:
    empty_state(
        "No contract analyzed yet",
        "Upload a PDF, DOCX, or paste text to begin.",
        "Tip: click 'Try Demo Contract' to explore the full experience.",
    )
    st.stop()

if st.session_state.get("is_demo"):
    demo_banner()

contract_text = st.session_state.get("contract_text", "")
if detect_contract_language and contract_text:
    lang = detect_contract_language(contract_text)
    st.caption(f"🌐 Detected language: {lang.title()}")

health = results.get("health_evaluation", {}) if isinstance(results, dict) else {}
clauses = (results.get("structured_clauses", {}) or {}).get("clauses", {}) if isinstance(results, dict) else {}

tab_overview, tab_clauses, tab_risk, tab_report = st.tabs(["Overview", "Clauses", "Risk Analysis", "Report"])

with tab_overview:
    left, right = st.columns([1, 2])
    with left:
        health_ring(int(health.get("health_score", 0) or 0))
    with right:
        st.markdown(f"**Executive summary** — {health.get('executive_summary', health.get('reasoning', 'No summary available.'))}")
        with st.expander("What does this score mean?"):
            st.markdown(
                "- **75–100:** Well-structured and ready for signing with minor review.\n"
                "- **50–74:** Requires legal review — key clauses present but incomplete.\n"
                "- **25–49:** Significant gaps — missing critical protections.\n"
                "- **0–24:** High risk — do not sign without legal counsel."
            )
    risk_heatmap(clauses)
    score_breakdown_bars(st.session_state.get("score_breakdown") or DEMO_SCORE_BREAKDOWN if st.session_state.get("is_demo") else [])

with tab_clauses:
    if not clauses:
        empty_state("No clauses extracted", "Run analysis to see clause-by-clause results.")
    for name, payload in clauses.items():
        status = str(payload.get("status", "missing"))
        css = {"found": "found", "not_found": "missing", "missing": "missing"}.get(status, "partial")
        st.markdown(f"<div class='clause-card {css}'><b>{name.replace('_', ' ').title()}</b> — {status}</div>", unsafe_allow_html=True)
        text = payload.get("extracted_text")
        if text and clause_readability:
            read = clause_readability(text)
            st.caption(f"{read['badge']} · {read['words_per_sentence']} words/sentence")
        snippets = payload.get("evidence_snippets") or []
        if snippets:
            evidence_block(snippets, title=f"Evidence — {name.replace('_', ' ').title()}")

with tab_risk:
    red_flags = health.get("red_flags", []) or []
    issues = health.get("issues", []) or []
    if not red_flags and not issues:
        empty_state("No risks detected", "The analysis did not flag specific risks.")
    for flag in sorted(red_flags, key=lambda f: {"high": 0, "medium": 1, "low": 2}.get(f.get("severity"), 3)):
        st.markdown(f"<div class='clause-card missing'><b>{flag.get('type', 'risk').replace('_', ' ').title()}</b> · {flag.get('severity', '')}</div>", unsafe_allow_html=True)
    for issue in issues:
        st.write(f"- {issue}")

with tab_report:
    st.subheader("Export")
    with st.expander("Export options"):
        st.download_button(
            "⬇️ Download JSON", data=json.dumps(results, indent=2, default=str),
            file_name="contract_analysis.json", mime="application/json",
        )
        csv_rows = ["clause_type,status,confidence,extracted_text"]
        for name, payload in clauses.items():
            text = str(payload.get("extracted_text") or "").replace("\n", " ").replace(",", ";")
            csv_rows.append(f"{name},{payload.get('status', '')},{payload.get('confidence', '')},{text}")
        st.download_button(
            "⬇️ Download CSV", data="\n".join(csv_rows),
            file_name="clauses.csv", mime="text/csv",
        )
    if st.button("Generate professional PDF report"):
        with st.spinner("Generating professional PDF report..."):
            st.toast("📋 Report ready", icon="📋")
            st.info("Use the Reports section to download the full PDF.")
