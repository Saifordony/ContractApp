from __future__ import annotations

from typing import Optional

import streamlit as st


def page_header(title: str, subtitle: str, eyebrow: Optional[str] = None) -> None:
    eyebrow_html = f"<div class='eyebrow'>{eyebrow}</div>" if eyebrow else ""
    st.markdown(
        f"""
        <div class='page-header-card'>
            {eyebrow_html}
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def workflow_stepper(steps: list[str], active_index: int = 0) -> None:
    html = "<div class='workflow-stepper'>"
    for idx, step in enumerate(steps):
        cls = "done" if idx < active_index else "active" if idx == active_index else "pending"
        html += f"<div class='workflow-step {cls}'><span>{idx + 1}</span>{step}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def topbar(username: str, ai_status: str = "Checking", selected_contract: str = "No contract selected") -> None:
    tone = "success" if ai_status.lower() == "online" else "danger" if ai_status.lower() == "offline" else "neutral"
    st.markdown(
        f"""
        <div class='topbar'>
            <div>
                <div class='topbar-title'>Contract Intelligence Platform</div>
                <div class='topbar-sub'>Current contract: {selected_contract}</div>
            </div>
            <div class='topbar-actions'>
                <span class='badge badge-{tone}'>AI {ai_status}</span>
                <span class='topbar-sub'>{username}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
