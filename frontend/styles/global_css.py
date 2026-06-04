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

        .brand-lockup {{ display:flex; align-items:center; gap:.65rem; margin:.35rem 0 1rem; }}
        .brand-mark {{ width:38px; height:38px; border-radius:13px; display:inline-flex; align-items:center; justify-content:center; background:linear-gradient(135deg,#172554,#4F46E5); color:#fff; font-weight:900; box-shadow:0 12px 28px rgba(79,70,229,.24); }}
        .brand-name {{ color:var(--primary); font-weight:850; letter-spacing:-.035em; font-size:1.12rem; }}
        .brand-subtitle {{ color:var(--muted); font-size:.82rem; margin-top:-.15rem; }}
        .auth-shell {{ min-height:calc(100vh - 7rem); display:grid; place-items:center; padding:2rem 1rem; background:radial-gradient(circle at 12% 20%, rgba(79,70,229,.16), transparent 34%), radial-gradient(circle at 86% 12%, rgba(37,99,235,.14), transparent 30%); }}
        .auth-card {{ width:min(980px,100%); display:grid; grid-template-columns:1.05fr .95fr; gap:1.2rem; background:rgba(255,255,255,.82); border:1px solid rgba(255,255,255,.78); border-radius:28px; box-shadow:0 26px 70px rgba(15,23,42,.14); backdrop-filter:blur(18px); padding:1.25rem; }}
        .auth-hero {{ border-radius:22px; background:linear-gradient(145deg,#172554 0%,#312E81 55%,#4F46E5 100%); padding:2rem; color:#fff; min-height:520px; display:flex; flex-direction:column; justify-content:space-between; }}
        .auth-hero * {{ color:#fff!important; }}
        .auth-hero h1 {{ color:#fff!important; font-size:2.4rem; line-height:1.05; margin:.7rem 0; }}
        .trust-list {{ display:grid; gap:.7rem; margin-top:1.5rem; }}
        .trust-item {{ background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.18); border-radius:14px; padding:.75rem .85rem; }}
        .auth-panel {{ padding:1.4rem 1.2rem; }}
        .auth-panel h2 {{ margin:.15rem 0 .2rem; color:var(--primary); letter-spacing:-.035em; }}
        .auth-panel p {{ color:var(--muted); margin:.1rem 0 1rem; }}
        .auth-panel .stTextInput input {{ border-radius:12px; border:1px solid var(--border); transition:all .18s ease; }}
        .auth-panel .stTextInput input:focus {{ border-color:var(--accent); box-shadow:0 0 0 4px rgba(79,70,229,.12); }}
        .auth-panel .stButton button, .auth-panel div[data-testid="stFormSubmitButton"] button {{ width:100%; border-radius:12px; background:linear-gradient(135deg,#172554,#4F46E5); color:#fff; border:0; font-weight:800; transition:transform .16s ease, box-shadow .16s ease; }}
        .auth-panel .stButton button:hover, .auth-panel div[data-testid="stFormSubmitButton"] button:hover {{ transform:translateY(-1px); box-shadow:0 14px 30px rgba(79,70,229,.22); }}
        .next-step-card {{ border:1px solid var(--border); background:#fff; border-radius:18px; padding:1rem 1.1rem; box-shadow:0 10px 30px rgba(15,23,42,.05); margin:.75rem 0; }}
        .next-step-card strong {{ color:var(--primary); }}
        @media (max-width: 900px) {{ .auth-card {{ grid-template-columns:1fr; }} .auth-hero {{ min-height:auto; }} }}
        div[data-testid="stDataFrame"] {{ border:1px solid var(--border); border-radius:14px; overflow:hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
