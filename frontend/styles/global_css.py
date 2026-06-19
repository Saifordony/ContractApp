from __future__ import annotations

import streamlit as st


def apply_global_css(sidebar_compact: bool = False, theme_mode: str = "light", direction: str = "ltr") -> None:
    sidebar_width = "5.5rem" if sidebar_compact else "18rem"
    sidebar_text_display = "none" if sidebar_compact else "block"
    is_dark = (theme_mode or "light").lower() == "dark"
    is_rtl = (direction or "ltr").lower() == "rtl"

    tokens = {
        "bg": "#0B1120" if is_dark else "#F7F9FC",
        "surface": "#111827" if is_dark else "#FFFFFF",
        "card": "#111827" if is_dark else "#FFFFFF",
        "primary": "#A5B4FC" if is_dark else "#172554",
        "accent": "#818CF8" if is_dark else "#4F46E5",
        "text": "#E5E7EB" if is_dark else "#111827",
        "muted": "#9CA3AF" if is_dark else "#6B7280",
        "border": "#273244" if is_dark else "#E5E7EB",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "danger": "#F87171" if is_dark else "#DC2626",
        "info": "#60A5FA" if is_dark else "#2563EB",
        "sidebar": "#020617" if is_dark else "#0F172A",
        "shadow": "0 12px 34px rgba(0,0,0,.28)" if is_dark else "0 10px 30px rgba(15,23,42,.06)",
    }
    rtl_css = """
        .stApp { direction: rtl; }
        .block-container, .page-header-card, .metric-card, .section-card, .empty-state, .chat-shell { text-align:right; }
        .topbar { direction: rtl; }
        .topbar-actions { flex-direction: row-reverse; }
        section[data-testid="stSidebar"] .stRadio label, section[data-testid="stSidebar"] .stSelectbox label { text-align:right; }
        .chat-row.user { justify-content:flex-start; }
        .chat-row.assistant { justify-content:flex-end; }
    """ if is_rtl else """
        .stApp { direction: ltr; }
        .block-container, .page-header-card, .metric-card, .section-card, .empty-state, .chat-shell { text-align:left; }
    """

    st.markdown(
        f"""
        <style>
        :root {{
            --bg:{tokens['bg']}; --surface:{tokens['surface']}; --card:{tokens['card']};
            --primary:{tokens['primary']}; --accent:{tokens['accent']}; --text:{tokens['text']};
            --muted:{tokens['muted']}; --border:{tokens['border']}; --success:{tokens['success']};
            --warning:{tokens['warning']}; --danger:{tokens['danger']}; --info:{tokens['info']};
        }}
        .stApp {{ background: var(--bg)!important; color: var(--text)!important; font-family: Inter, "Segoe UI", Tahoma, Arial, sans-serif; }}
        .stApp::before {{ display:none!important; }}
        .block-container {{ max-width: 1280px; padding-top: 1.25rem; padding-bottom: 3rem; }}
        section[data-testid="stSidebar"] {{ background: {tokens['sidebar']}!important; min-width:{sidebar_width}!important; max-width:{sidebar_width}!important; border-right:1px solid rgba(255,255,255,.08); }}
        section[data-testid="stSidebar"] * {{ color:#E5E7EB!important; }}
        section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {{ display:{sidebar_text_display}; }}
        .topbar, .page-header-card, .metric-card, .section-card, .chat-shell, .empty-state, .feature-card, .next-step-card {{ background:var(--card)!important; border:1px solid var(--border)!important; border-radius:18px; box-shadow:{tokens['shadow']}; color:var(--text)!important; }}
        .topbar {{ display:flex; align-items:center; justify-content:space-between; padding:1rem 1.15rem; margin-bottom:1rem; }}
        .topbar-title {{ font-weight:750; color:var(--primary)!important; letter-spacing:-.02em; }}
        .topbar-sub, .metric-sub, .metric-label, .section-card-sub, .empty-subtitle, .page-header-card p, .feature-card p {{ color:var(--muted)!important; }}
        .topbar-actions {{ display:flex; gap:.75rem; align-items:center; }}
        .page-header-card {{ padding:1.35rem 1.5rem; margin-bottom:1rem; }}
        .page-header-card h1 {{ margin:0; color:var(--primary)!important; font-size:2rem; letter-spacing:-.04em; }}
        .eyebrow {{ color:var(--accent)!important; font-size:.78rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.4rem; }}
        .metric-card {{ padding:1rem; min-height:112px; }}
        .metric-label {{ font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; font-weight:750; }}
        .metric-value {{ color:var(--text)!important; font-size:1.55rem; font-weight:800; margin:.25rem 0; }}
        .section-card {{ padding:1rem 1.1rem; margin:.6rem 0; }}
        .section-card-title {{ color:var(--primary)!important; font-weight:800; font-size:1rem; }}
        .empty-state {{ padding:1.4rem; margin:1rem 0; }}
        .empty-title {{ color:var(--text)!important; font-weight:800; font-size:1.15rem; }}
        .empty-action {{ color:var(--accent)!important; font-weight:700; margin-top:.6rem; }}
        .badge {{ padding:.35rem .65rem; border-radius:999px; font-size:.78rem; font-weight:750; border:1px solid var(--border); }}
        .badge-success {{ color:var(--success)!important; background:rgba(34,197,94,.12); }}
        .badge-warning {{ color:var(--warning)!important; background:rgba(245,158,11,.12); }}
        .badge-danger {{ color:var(--danger)!important; background:rgba(248,113,113,.13); }}
        .badge-neutral {{ color:var(--muted)!important; background:rgba(148,163,184,.12); }}
        .workflow-stepper {{ display:flex; gap:.65rem; flex-wrap:wrap; margin:.75rem 0 1rem; }}
        .workflow-step {{ background:var(--card); border:1px solid var(--border); border-radius:999px; padding:.55rem .75rem; color:var(--muted); font-weight:650; }}
        .workflow-step span {{ display:inline-flex; align-items:center; justify-content:center; width:1.4rem; height:1.4rem; border-radius:50%; margin-inline-end:.35rem; background:rgba(79,70,229,.12); color:var(--accent); }}
        .workflow-step.active, .workflow-step.done {{ color:var(--text); border-color:var(--accent); }}
        .chat-shell {{ padding:1rem; margin:.8rem 0; }}
        .chat-scroll {{ display:flex; flex-direction:column; gap:.75rem; }}
        .chat-row {{ display:flex; }}
        .chat-row.user {{ justify-content:flex-end; }}
        .chat-row.assistant {{ justify-content:flex-start; }}
        .chat-bubble {{ max-width:76%; padding:.78rem .95rem; border-radius:16px; line-height:1.45; }}
        .chat-bubble.user {{ background:var(--accent); color:white!important; border-bottom-right-radius:5px; }}
        .chat-bubble.assistant {{ background:{'#1F2937' if is_dark else '#F3F4F6'}; color:var(--text)!important; border-bottom-left-radius:5px; }}
        .feature-card {{ padding:1rem; margin:.5rem 0; min-height:138px; transition:transform .18s ease, border-color .18s ease; }}
        .feature-card:hover, .metric-card:hover {{ transform:translateY(-2px); border-color:var(--accent)!important; }}
        .feature-icon {{ width:2rem; height:2rem; border-radius:10px; display:flex; align-items:center; justify-content:center; background:rgba(79,70,229,.13); color:var(--accent); font-weight:800; margin-bottom:.6rem; }}
        .next-step-card {{ padding:.95rem 1rem; margin:.8rem 0; }}
        button, .stButton button {{ transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease; }}
        .stButton button:hover {{ transform:translateY(-1px); box-shadow:0 10px 24px rgba(79,70,229,.18); }}
        input:focus, textarea:focus {{ border-color:var(--accent)!important; box-shadow:0 0 0 3px rgba(79,70,229,.16)!important; }}
        {rtl_css}
        </style>
        """,
        unsafe_allow_html=True,
    )

    apply_premium_components_css()


def apply_premium_components_css() -> None:
    """Premium "legal intelligence" component classes (Dimension 2.1).

    Injected in addition to the base theme so the redesigned components
    (stat cards, severity-coded clause cards, gradient chat bubbles, confidence
    badges, styled evidence quotes) are available on every page without
    disturbing the base design tokens.
    """
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;700&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
        <style>
        :root {
            --card-hover:#172038; --accent-light:#6B97FF; --accent-2:#8B6CF0; --accent-3:#2DD4BF;
            --subtle:#344263;
            --glow-blue:rgba(79,127,239,0.20); --glow-purple:rgba(139,108,240,0.20); --glow-teal:rgba(45,212,191,0.15);
            --shadow-sm:0 2px 8px rgba(0,0,0,0.3); --shadow-md:0 8px 24px rgba(0,0,0,0.4); --shadow-lg:0 16px 48px rgba(0,0,0,0.5);
            --radius-sm:8px; --radius-md:14px; --radius-lg:20px;
        }
        @keyframes fadeInUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
        @keyframes ringDraw { from { stroke-dashoffset:326.7; } }
        .stat-card, .clause-card, .section-card { animation: fadeInUp 0.3s ease both; }
        .stat-card:nth-child(1) { animation-delay:0.05s; }
        .stat-card:nth-child(2) { animation-delay:0.10s; }
        .stat-card:nth-child(3) { animation-delay:0.15s; }
        .stat-card {
            background:var(--card); border:1px solid var(--subtle); border-radius:var(--radius-md);
            padding:1.25rem 1.5rem; position:relative; overflow:hidden;
            transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease;
        }
        .stat-card::before {
            content:''; position:absolute; top:0; left:0; right:0; height:3px;
            background:linear-gradient(90deg, var(--accent), var(--accent-2));
            border-radius:var(--radius-md) var(--radius-md) 0 0;
        }
        .stat-card:hover { transform:translateY(-2px); box-shadow:var(--shadow-md); border-color:var(--accent); }
        .stat-card .stat-value { font-family:'Playfair Display',serif; font-size:1.9rem; font-weight:700; }
        .stat-card .stat-label { font-family:'DM Sans',sans-serif; color:var(--muted); font-size:.8rem; text-transform:uppercase; letter-spacing:.04em; }
        .clause-card { border-left:4px solid var(--subtle); padding:.85rem 1rem; border-radius:var(--radius-sm); background:var(--card); margin:.5rem 0; }
        .clause-card.found { border-left-color:var(--success); }
        .clause-card.partial { border-left-color:var(--warning); }
        .clause-card.missing { border-left-color:var(--danger); }
        .clause-card.low-confidence { border-left-color:var(--accent-2); }
        .chat-bubble.user { background:linear-gradient(135deg, var(--accent), var(--accent-2)); box-shadow:0 4px 16px var(--glow-blue); }
        .chat-bubble.assistant { background:var(--card); border:1px solid var(--subtle); }
        .confidence-badge { display:inline-flex; align-items:center; gap:4px; padding:2px 10px; border-radius:999px; font-size:.72rem; font-weight:600; }
        .confidence-high { background:rgba(34,214,143,0.15); color:var(--success); }
        .confidence-medium { background:rgba(245,158,11,0.15); color:var(--warning); }
        .confidence-low { background:rgba(239,68,68,0.15); color:var(--danger); }
        .evidence-quote {
            background:rgba(79,127,239,0.08); border-left:3px solid var(--accent);
            border-radius:0 var(--radius-sm) var(--radius-sm) 0; padding:.75rem 1rem;
            font-family:'DM Mono',monospace; font-size:.85rem; color:var(--primary); margin:.5rem 0; line-height:1.6;
        }
        .display-heading { font-family:'Playfair Display',serif; }
        </style>
        """,
        unsafe_allow_html=True,
    )
