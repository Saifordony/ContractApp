"""Home / dashboard: KPI stat cards, recent contracts, onboarding."""

from __future__ import annotations

import streamlit as st

from frontend.auth import require_auth
from frontend.components.onboarding_banner import onboarding_banner
from frontend.components.sidebar import api_base_url, render_app_sidebar
from frontend.components.ui import stat_card
from frontend.services.api_client import request_json
from frontend.styles.global_css import apply_global_css

st.set_page_config(page_title="Home · Contract Intelligence", page_icon="🏠", layout="wide")
apply_global_css(theme_mode=st.session_state.get("theme_mode", "dark"))
require_auth()
render_app_sidebar()

st.markdown("<h1 class='display-heading'>Dashboard</h1>", unsafe_allow_html=True)

with st.spinner("Loading your workspace summary..."):
    stats = request_json(api_base_url(), "/stats/summary", token=st.session_state.get("token"))

if isinstance(stats, dict) and not stats.get("error"):
    col1, col2, col3 = st.columns(3)
    with col1:
        stat_card("Total Contracts Analyzed", str(stats.get("total_contracts", 0)))
    with col2:
        last = stats.get("last_analysis_date") or "—"
        stat_card("Last Analysis Date", str(last)[:10])
    with col3:
        stat_card("Average Health Score", f"{stats.get('average_health_score', 0)}/100")

    dist = stats.get("health_distribution", {})
    st.caption(
        f"Health distribution — 🟢 {dist.get('high', 0)} healthy · "
        f"🟡 {dist.get('medium', 0)} needs review · 🔴 {dist.get('low', 0)} high risk"
    )

    st.subheader("Recent Contracts")
    contracts = request_json(api_base_url(), "/contracts", token=st.session_state.get("token"))
    rows = contracts.get("contracts", []) if isinstance(contracts, dict) else []
    if rows:
        st.dataframe(
            [{"Title": c.get("title", ""), "Status": c.get("status", "")} for c in rows[:5]],
            use_container_width=True,
        )
    else:
        st.info("No contracts yet. Head to Analysis to upload your first contract.")
else:
    message = stats.get("message") if isinstance(stats, dict) else "Backend unavailable."
    st.warning(f"Could not load dashboard stats: {message}")

onboarding_banner()
