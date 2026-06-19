"""Chat page: grouped messages, confidence badge, evidence, response-mode pills."""

from __future__ import annotations

import streamlit as st

from frontend.auth import require_auth
from frontend.components.alerts import empty_state
from frontend.components.evidence_block import evidence_block
from frontend.components.sidebar import api_base_url, render_app_sidebar
from frontend.components.ui import confidence_badge
from frontend.services.api_client import request_json
from frontend.styles.global_css import apply_global_css

st.set_page_config(page_title="Chat · Contract Intelligence", page_icon="💬", layout="wide")
apply_global_css(theme_mode=st.session_state.get("theme_mode", "dark"))
require_auth()
render_app_sidebar()

st.markdown("<h1 class='display-heading'>Chat with your contract</h1>", unsafe_allow_html=True)

contract_text = st.session_state.get("contract_text", "")
if not contract_text:
    empty_state("Nothing to chat about yet", "Upload and analyze a contract first to start chatting.")
    st.stop()

st.session_state.setdefault("chat_history", [])

# Response-mode pill toggle (not a selectbox).
MODES = ["Ask Anything", "Simple", "Detailed", "Risk Review", "Rewrite"]
mode_cols = st.columns(len(MODES))
for i, label in enumerate(MODES):
    if mode_cols[i].button(label, use_container_width=True):
        st.session_state["response_mode"] = label.lower().replace(" ", "_")
active_mode = st.session_state.get("response_mode", "ask_anything")
st.caption(f"Mode: {active_mode.replace('_', ' ').title()}")

top_cols = st.columns([1, 1])
if top_cols[0].button("🧹 Clear Chat", use_container_width=True):
    st.session_state["chat_history"] = []
with top_cols[1].expander("Contract text preview"):
    st.text(contract_text[:4000])

# Render history.
for msg in st.session_state["chat_history"]:
    role = msg.get("role", "assistant")
    with st.chat_message("user" if role == "user" else "assistant"):
        st.write(msg.get("content", ""))
        if role == "assistant":
            if msg.get("confidence_score") is not None:
                confidence_badge(msg["confidence_score"])
            if msg.get("evidence_snippets"):
                evidence_block(msg["evidence_snippets"], title="Evidence")
            for fup in msg.get("suggested_followups", [])[:3]:
                st.caption(f"💡 {fup}")

prompt = st.chat_input("Ask about termination, payment, risks, missing clauses...")
if prompt:
    if not prompt.strip():
        st.stop()
    st.session_state["chat_history"].append({"role": "user", "content": prompt})
    with st.spinner("Retrieving relevant clauses..."):
        resp = request_json(
            api_base_url(), "/genai/contract-chat", method="POST",
            token=st.session_state.get("token"),
            data={
                "message": prompt,
                "response_mode": active_mode,
                "response_language": st.session_state.get("ui_language", "english"),
                "chat_history": st.session_state["chat_history"][-6:],
            },
            timeout=180,
        )
    if isinstance(resp, dict) and resp.get("error"):
        st.session_state["chat_history"].append({"role": "assistant", "content": resp.get("message", "Sorry, something went wrong.")})
    else:
        st.session_state["chat_history"].append(
            {
                "role": "assistant",
                "content": resp.get("answer", ""),
                "confidence_score": resp.get("confidence_score"),
                "evidence_snippets": resp.get("evidence_snippets", []),
                "suggested_followups": resp.get("suggested_followups", []),
            }
        )
    st.rerun()
