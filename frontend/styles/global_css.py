from __future__ import annotations

import streamlit as st


def apply_global_css(sidebar_compact: bool = False) -> None:
    sidebar_width = "5.5rem" if sidebar_compact else "18rem"
    sidebar_text_display = "none" if sidebar_compact else "block"
    st.markdown(
        f"""
        <style>
        :root {{
            --bg:#F7F9FC; --card:#FFFFFF; --primary:#172554; --accent:#4F46E5;
            --text:#111827; --muted:#6B7280; --border:#E5E7EB;
            --success:#16A34A; --warning:#D97706; --danger:#DC2626; --info:#2563EB;
        }}
        .stApp {{ background: var(--bg); color: var(--text); font-family: Inter, "Segoe UI", sans-serif; }}
        .stApp::before {{ display:none!important; }}
        .block-container {{ max-width: 1280px; padding-top: 1.25rem; padding-bottom: 3rem; }}
        section[data-testid="stSidebar"] {{ background: #0F172A; min-width:{sidebar_width}!important; max-width:{sidebar_width}!important; border-right:1px solid rgba(255,255,255,.08); }}
        section[data-testid="stSidebar"] * {{ color:#E5E7EB!important; }}
        section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {{ display:{sidebar_text_display}; }}
        .topbar, .page-header-card, .metric-card, .section-card, .chat-shell, .empty-state {{ background:var(--card); border:1px solid var(--border); border-radius:18px; box-shadow:0 10px 30px rgba(15,23,42,.06); }}
        .topbar {{ display:flex; align-items:center; justify-content:space-between; padding:1rem 1.15rem; margin-bottom:1rem; }}
        .topbar-title {{ font-weight:750; color:var(--primary); letter-spacing:-.02em; }}
        .topbar-sub {{ color:var(--muted); font-size:.9rem; }}
        .topbar-actions {{ display:flex; gap:.75rem; align-items:center; }}
        .page-header-card {{ padding:1.35rem 1.5rem; margin-bottom:1rem; }}
        .page-header-card h1 {{ margin:0; color:var(--primary); font-size:2rem; letter-spacing:-.04em; }}
        .page-header-card p {{ margin:.35rem 0 0; color:var(--muted); }}
        .eyebrow {{ color:var(--accent); text-transform:uppercase; letter-spacing:.08em; font-size:.75rem; font-weight:700; }}
        .metric-card {{ padding:1rem; min-height:112px; }}
        .metric-label {{ color:var(--muted); font-size:.82rem; font-weight:650; text-transform:uppercase; letter-spacing:.04em; }}
        .metric-value {{ font-size:1.85rem; font-weight:800; color:var(--primary); margin-top:.25rem; }}
        .metric-sub {{ color:var(--muted); font-size:.88rem; }}
        .section-card {{ padding:1rem 1.1rem; margin:.75rem 0; }}
        .section-card-title {{ font-weight:750; color:var(--primary); }}
        .section-card-sub {{ color:var(--muted); margin-top:.25rem; }}
        .badge {{ display:inline-flex; align-items:center; padding:.25rem .55rem; border-radius:999px; font-size:.78rem; font-weight:700; border:1px solid var(--border); }}
        .badge-success {{ background:#DCFCE7; color:#166534; border-color:#BBF7D0; }}
        .badge-warning, .badge-orange {{ background:#FEF3C7; color:#92400E; border-color:#FDE68A; }}
        .badge-danger {{ background:#FEE2E2; color:#991B1B; border-color:#FECACA; }}
        .badge-neutral {{ background:#F3F4F6; color:#374151; }}
        .workflow-stepper {{ display:flex; flex-wrap:wrap; gap:.5rem; margin:1rem 0; }}
        .workflow-step {{ background:#fff; border:1px solid var(--border); border-radius:999px; padding:.55rem .8rem; color:var(--muted); font-weight:650; }}
        .workflow-step span {{ background:#EEF2FF; color:var(--accent); border-radius:999px; padding:.15rem .45rem; margin-right:.35rem; }}
        .workflow-step.done {{ border-color:#BBF7D0; color:#166534; }} .workflow-step.active {{ border-color:#C7D2FE; color:var(--primary); box-shadow:0 8px 20px rgba(79,70,229,.10); }}
        .empty-state {{ padding:2rem; text-align:center; margin:1rem 0; }} .empty-title {{ font-size:1.25rem; font-weight:760; color:var(--primary); }} .empty-subtitle,.empty-action {{ color:var(--muted); margin-top:.35rem; }}
        .chat-shell {{ padding:1rem; }} .chat-scroll {{ max-height:430px; overflow-y:auto; padding-right:.25rem; }}
        .chat-row {{ display:flex; margin:.65rem 0; }} .chat-row.user {{ justify-content:flex-end; }}
        .chat-bubble {{ max-width:78%; padding:.8rem 1rem; border-radius:18px; line-height:1.5; border:1px solid var(--border); }}
        .chat-bubble.assistant {{ background:#fff; color:var(--text); border-top-left-radius:6px; }}
        .chat-bubble.user {{ background:var(--primary); color:#fff; border-color:var(--primary); border-top-right-radius:6px; }}
        div[data-testid="stDataFrame"] {{ border:1px solid var(--border); border-radius:14px; overflow:hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
