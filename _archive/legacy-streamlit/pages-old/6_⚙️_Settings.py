"""Settings page: profile, LLM config display, theme + language toggles."""

from __future__ import annotations

import streamlit as st

from frontend.auth import clear_session, require_auth
from frontend.components.sidebar import api_base_url, llm_status_indicator, render_app_sidebar
from frontend.services.api_client import request_json
from frontend.styles.global_css import apply_global_css

st.set_page_config(page_title="Settings · Contract Intelligence", page_icon="⚙️", layout="wide")
apply_global_css(theme_mode=st.session_state.get("theme_mode", "dark"))
require_auth()
render_app_sidebar()

st.markdown("<h1 class='display-heading'>Settings</h1>", unsafe_allow_html=True)

st.subheader("Profile")
st.write(f"Signed in as **{st.session_state.get('username', 'user')}**")

st.subheader("Appearance")
col1, col2 = st.columns(2)
with col1:
    theme = st.selectbox("Theme", ["dark", "light"], index=0 if st.session_state.get("theme_mode", "dark") == "dark" else 1)
    st.session_state["theme_mode"] = theme
with col2:
    lang = st.selectbox("Language / اللغة", ["english", "arabic"], index=0 if st.session_state.get("ui_language", "english") == "english" else 1)
    st.session_state["ui_language"] = lang

st.subheader("LLM configuration")
health = request_json(api_base_url(), "/llm/health", token=st.session_state.get("token"))
if isinstance(health, dict) and not health.get("error"):
    st.caption(llm_status_indicator(health))
    st.json({k: health.get(k) for k in ("ai_provider", "model", "base_url", "reachable", "num_ctx")})
else:
    st.caption("🔴 LLM offline · Keyword mode")

st.subheader("Session")
if st.button("Sign out"):
    clear_session()
    st.toast("Signed out", icon="👋")
    st.rerun()
