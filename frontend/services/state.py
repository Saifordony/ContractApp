from __future__ import annotations

import streamlit as st

DEFAULTS = {
    "token": None,
    "username": None,
    "selected_client_id": None,
    "selected_contract_id": None,
    "analysis_result": None,
    "readiness_result": None,
    "benchmark_result": None,
    "chat_messages_by_contract": {},
    "last_api_error": None,
    "last_chat_error": None,
    "sidebar_compact": False,
    "ui_language": "en",
    "theme_mode": "light",
}


def init_session_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, dict) else value


def clear_session() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()


def select_contract(contract_id: str | None) -> None:
    st.session_state.selected_contract_id = contract_id
    if contract_id and contract_id not in st.session_state.chat_messages_by_contract:
        st.session_state.chat_messages_by_contract[contract_id] = []
