"""Pipeline analytics: opportunity entry, KPIs, funnel chart, stale deals."""

from __future__ import annotations

import json

import streamlit as st

from frontend.auth import require_auth
from frontend.components.sidebar import api_base_url, render_app_sidebar
from frontend.components.ui import stat_card
from frontend.services.api_client import request_json
from frontend.styles.global_css import apply_global_css

st.set_page_config(page_title="Pipeline · Contract Intelligence", page_icon="🔀", layout="wide")
apply_global_css(theme_mode=st.session_state.get("theme_mode", "dark"))
require_auth()
render_app_sidebar()

st.markdown("<h1 class='display-heading'>Pipeline Analytics</h1>", unsafe_allow_html=True)
st.session_state.setdefault("opportunities", [])

# --- Input: JSON upload OR manual entry -------------------------------------------
up = st.file_uploader("Upload opportunities JSON", type=["json"])
if up is not None:
    try:
        st.session_state["opportunities"] = json.loads(up.read().decode("utf-8"))
        st.toast("✅ Opportunities loaded", icon="✅")
    except Exception:
        st.error("That file is not valid JSON.")

with st.form("add_opportunity"):
    cols = st.columns(5)
    name = cols[0].text_input("Name")
    stage = cols[1].selectbox("Stage", ["Lead", "Qualified", "Proposal", "Negotiation", "Won", "Lost"])
    value = cols[2].number_input("Value", min_value=0.0, step=1000.0)
    last_updated = cols[3].text_input("Last updated (YYYY-MM-DD)")
    owner = cols[4].text_input("Owner")
    if st.form_submit_button("Add Opportunity") and name:
        st.session_state["opportunities"].append(
            {"opportunity_name": name, "client": name, "stage": stage, "value": value,
             "last_updated": last_updated, "owner": owner}
        )

opportunities = st.session_state["opportunities"]
if not opportunities:
    st.info("Add opportunities or upload a JSON file to see pipeline analytics.")
    st.stop()

with st.spinner("Crunching pipeline analytics..."):
    result = request_json(
        api_base_url(), "/pipeline/analyze", method="POST",
        token=st.session_state.get("token"), data={"opportunities": opportunities},
        timeout=120,
    )

if not isinstance(result, dict) or result.get("error"):
    st.warning(result.get("message", "Could not analyze pipeline.") if isinstance(result, dict) else "Failed.")
    st.stop()

kpis = result.get("kpis", result)
c1, c2, c3, c4 = st.columns(4)
with c1:
    stat_card("Total Pipeline", str(kpis.get("total_pipeline", 0)))
with c2:
    stat_card("Weighted Pipeline", str(kpis.get("weighted_pipeline", 0)))
with c3:
    stat_card("Open Opportunities", str(kpis.get("open_opportunities", len(opportunities))))
with c4:
    stat_card("Coverage Ratio", str(kpis.get("coverage_ratio", "—")))

stage_counts = result.get("stage_counts", {})
if stage_counts:
    try:
        import plotly.graph_objects as go

        fig = go.Figure(go.Funnel(
            y=list(stage_counts.keys()), x=list(stage_counts.values()),
            textinfo="value+percent initial",
            marker={"color": ["#4F7FEF", "#6B97FF", "#8B6CF0", "#2DD4BF", "#22D68F", "#F59E0B"]},
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#D4E2FF")
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.bar_chart(stage_counts)

stale = result.get("stale_deals", [])
if stale:
    st.subheader("Stale deals")
    st.dataframe(stale, use_container_width=True)

for rec in result.get("recommendations", []):
    st.markdown(f"<div class='clause-card partial'>{rec}</div>", unsafe_allow_html=True)
