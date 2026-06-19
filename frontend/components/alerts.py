from __future__ import annotations

from typing import Any

import streamlit as st


def friendly_error(message: str, next_step: str | None = None, technical_detail: Any | None = None) -> None:
    st.error(message)
    if next_step:
        st.caption(next_step)
    if technical_detail:
        with st.expander("Technical details"):
            st.write(technical_detail)


def empty_state(title: str, subtitle: str, action: str | None = None) -> None:
    st.markdown(
        f"""
        <div class='empty-state'>
            <div class='empty-title'>{title}</div>
            <div class='empty-subtitle'>{subtitle}</div>
            {f"<div class='empty-action'>{action}</div>" if action else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
