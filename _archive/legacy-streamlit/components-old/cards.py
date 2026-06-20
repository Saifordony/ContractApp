from __future__ import annotations

import html
from typing import Any

import streamlit as st


def metric_card(title: str, value: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>{html.escape(str(title))}</div>
            <div class='metric-value'>{html.escape(str(value))}</div>
            <div class='metric-sub'>{html.escape(str(subtitle))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_card(title: str, subtitle: str = "", icon: str = "") -> None:
    st.markdown(
        f"""
        <div class='section-card'>
            <div class='section-card-title'>{icon} {html.escape(str(title))}</div>
            <div class='section-card-sub'>{html.escape(str(subtitle))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
