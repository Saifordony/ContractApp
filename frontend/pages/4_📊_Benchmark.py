"""Benchmark page: radar chart (contract vs MENA average) + comparison table."""

from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from frontend.auth import require_auth
from frontend.components.alerts import empty_state
from frontend.components.sidebar import api_base_url, render_app_sidebar
from frontend.services.api_client import request_json
from frontend.styles.global_css import apply_global_css

st.set_page_config(page_title="Benchmark · Contract Intelligence", page_icon="📊", layout="wide")
apply_global_css(theme_mode=st.session_state.get("theme_mode", "dark"))
require_auth()
render_app_sidebar()

RADAR_AXES = ["Payment Terms", "Termination", "Liability", "Confidentiality", "Governing Law", "SLA"]
RADAR_KEYS = ["payment_terms", "termination", "liability", "confidentiality", "governing_law", "sla"]


def render_benchmark_radar(clause_results: List[Dict[str, Any]], mena_averages: Dict[str, Any]) -> None:
    """Plotly radar of contract score vs MENA market average (guarded import)."""
    try:
        import plotly.graph_objects as go
    except Exception:
        st.info("Install plotly to see the radar chart. Showing the comparison table below.")
        return

    contract_scores = [
        next((r.get("clause_score") for r in clause_results if r.get("clause_type") == k), 0)
        for k in RADAR_KEYS
    ]
    market_scores = [mena_averages.get(k, 65) for k in RADAR_KEYS]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=contract_scores, theta=RADAR_AXES, fill="toself",
                                  name="Your contract", line_color="#4F7FEF",
                                  fillcolor="rgba(79,127,239,0.35)"))
    fig.add_trace(go.Scatterpolar(r=market_scores, theta=RADAR_AXES, fill="toself",
                                  name="MENA market avg", line_color="#8B6CF0",
                                  fillcolor="rgba(139,108,240,0.12)"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#D4E2FF", polar=dict(bgcolor="rgba(14,21,37,1)"),
    )
    st.plotly_chart(fig, use_container_width=True)


st.markdown("<h1 class='display-heading'>Benchmark Comparison</h1>", unsafe_allow_html=True)

contract_text = st.session_state.get("contract_text", "")
if not contract_text:
    empty_state("No benchmark data yet", "Ingest the MENA seed dataset and analyze a contract to enable comparisons.")
    st.stop()

with st.spinner("Comparing against MENA market benchmarks..."):
    data = request_json(
        api_base_url(), "/benchmark/compare", method="POST",
        token=st.session_state.get("token"), data={"contract_text": contract_text},
        timeout=180,
    )

if not isinstance(data, dict) or data.get("error"):
    empty_state("No benchmark data yet", "Run Benchmark Comparison once a contract is analyzed.")
    st.stop()

clause_results = data.get("clause_results", [])
render_benchmark_radar(clause_results, data.get("mena_averages", {}))

if clause_results:
    st.subheader("Clause-by-clause comparison")
    st.dataframe(
        [
            {
                "Clause": r.get("clause_type", ""),
                "Your score": r.get("clause_score", ""),
                "Market avg": r.get("market_score", ""),
                "Suggested revision": r.get("suggested_revision", ""),
            }
            for r in clause_results
        ],
        use_container_width=True,
    )

if st.button("Download Benchmark Report"):
    st.toast("📋 Benchmark report ready", icon="📋")
