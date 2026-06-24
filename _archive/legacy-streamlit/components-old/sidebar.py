"""Redesigned application sidebar: brand mark, contract health, LLM status, timer."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import streamlit as st

from frontend.auth import render_session_timer
from frontend.build_info import APP_BUILD
from frontend.components.health_ring import health_ring


def api_base_url() -> str:
    return st.session_state.get("api_base") or os.getenv("BACKEND_URL", "http://localhost:8000")


def llm_status_indicator(health: Optional[Dict[str, Any]]) -> str:
    """Map an /llm/health-style payload to a colored status line."""
    if not health:
        return "🔴 LLM offline · Keyword mode"
    reachable = health.get("reachable")
    models = health.get("available_models") or []
    model = health.get("model")
    if reachable and model in models:
        return f"🟢 {model} · Ready"
    if reachable:
        return "🟡 Ollama reachable · Model loading"
    return "🔴 LLM offline · Keyword mode"


def render_brand() -> None:
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.75rem;">
          <div style="width:38px;height:38px;border-radius:10px;
               background:linear-gradient(135deg,#4F7FEF,#8B6CF0);color:#fff;
               display:flex;align-items:center;justify-content:center;font-weight:800;
               font-family:'DM Sans',sans-serif;">CI</div>
          <div style="font-family:'Playfair Display',serif;font-size:1.05rem;color:#D4E2FF;">
            Contract Intelligence</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_app_sidebar(*, llm_health: Optional[Dict[str, Any]] = None) -> None:
    """Render the shared sidebar chrome inside a `with st.sidebar:` context."""
    with st.sidebar:
        render_brand()

        analysis = st.session_state.get("analysis_results")
        if isinstance(analysis, dict):
            health = analysis.get("health_evaluation", {})
            score = health.get("health_score")
            if score is not None:
                health_ring(int(score), label=st.session_state.get("contract_title", "Current contract"))

        st.markdown("---")
        st.caption(llm_status_indicator(llm_health))
        render_session_timer()
        st.caption(f"build {APP_BUILD}")
