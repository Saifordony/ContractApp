"""Centralized Streamlit CSS for the active Contract Intelligence frontend."""

LIGHT_TOKENS = {
    "bg": "#F8FAFC",
    "surface": "#F8FAFC",
    "surface_strong": "#FFFFFF",
    "card": "#ffffff",
    "elevated": "#ffffff",
    "input_bg": "#F8FAFC",
    "input_text": "#0F172A",
    "border": "#e2e8f0",
    "border_strong": "#dbeafe",
    "text": "#0f172a",
    "muted": "#64748B",
    "accent": "#2563eb",
    "accent_soft": "#EFF6FF",
    "accent_text": "#1D4ED8",
    "success_bg": "#dcfce7",
    "success_text": "#166534",
    "warning_bg": "#fef3c7",
    "warning_text": "#92400e",
    "danger_bg": "#fee2e2",
    "danger_text": "#991b1b",
    "shadow": "0 18px 50px rgba(15,23,42,.08)",
}

DARK_TOKENS = {
    "bg": "#0F172A",
    "surface": "#1E293B",
    "surface_strong": "#111827",
    "card": "#1E293B",
    "elevated": "#243044",
    "input_bg": "#1E293B",
    "input_text": "#F8FAFC",
    "border": "#334155",
    "border_strong": "#1e40af",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "accent": "#3B82F6",
    "accent_soft": "#2563EB",
    "accent_text": "#FFFFFF",
    "success_bg": "#052e16",
    "success_text": "#86efac",
    "warning_bg": "#422006",
    "warning_text": "#fcd34d",
    "danger_bg": "#450a0a",
    "danger_text": "#fca5a5",
    "shadow": "0 18px 50px rgba(0,0,0,.28)",
}


def build_app_css(theme: str = "light", direction: str = "ltr") -> str:
    tokens = DARK_TOKENS if theme == "dark" else LIGHT_TOKENS
    align = "right" if direction == "rtl" else "left"
    reverse_align = "left" if direction == "rtl" else "right"
    return f"""
<style>
:root {{
  --cip-bg: {tokens['bg']};
  --cip-surface: {tokens['surface']};
  --cip-surface-strong: {tokens['surface_strong']};
  --cip-card: {tokens['card']};
  --cip-elevated: {tokens['elevated']};
  --cip-input-bg: {tokens['input_bg']};
  --cip-input-text: {tokens['input_text']};
  --cip-border: {tokens['border']};
  --cip-border-strong: {tokens['border_strong']};
  --cip-text: {tokens['text']};
  --cip-muted: {tokens['muted']};
  --cip-accent: {tokens['accent']};
  --cip-accent-soft: {tokens['accent_soft']};
  --cip-accent-text: {tokens['accent_text']};
  --cip-success-bg: {tokens['success_bg']};
  --cip-success-text: {tokens['success_text']};
  --cip-warning-bg: {tokens['warning_bg']};
  --cip-warning-text: {tokens['warning_text']};
  --cip-danger-bg: {tokens['danger_bg']};
  --cip-danger-text: {tokens['danger_text']};
  --cip-shadow: {tokens['shadow']};
  --cip-nav-active-bg: #2563EB;
  --cip-nav-active-text: #FFFFFF;
  --cip-nav-hover-bg: {"#334155" if theme == "dark" else "#EFF6FF"};
  --cip-nav-inactive-bg: {"#1E293B" if theme == "dark" else "transparent"};
  --cip-nav-inactive-text: {"#CBD5E1" if theme == "dark" else "#334155"};
  --cip-button-primary-bg: #2563EB;
  --cip-button-primary-text: #FFFFFF;
  --cip-button-secondary-bg: {"#1E293B" if theme == "dark" else "#FFFFFF"};
  --cip-button-secondary-text: {"#F8FAFC" if theme == "dark" else "#0F172A"};
}}
[data-testid="stAppViewContainer"] {{ background: var(--cip-bg); color: var(--cip-text); }}
[data-testid="stSidebar"] {{ background: var(--cip-surface-strong); border-{reverse_align}: 1px solid var(--cip-border); }}
[data-testid="stSidebar"] * {{ color: var(--cip-text); }}
[data-testid="stSidebar"] .stButton > button {{ background:var(--cip-nav-inactive-bg) !important; color:var(--cip-nav-inactive-text) !important; border:1px solid var(--cip-border) !important; border-radius:14px !important; min-height:2.75rem; justify-content:flex-start; text-align:{align}; padding:.55rem .75rem; }}
[data-testid="stSidebar"] .stButton > button:hover {{ background:var(--cip-nav-hover-bg) !important; color:var(--cip-text) !important; border-color:var(--cip-accent) !important; }}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, [data-testid="stSidebar"] label {{ color:var(--cip-muted) !important; }}
.block-container {{ max-width: 1240px; padding-top: 1.25rem; direction: {direction}; text-align: {align}; }}
h1, h2, h3, h4, h5, h6, p, label, span {{ color: inherit; }}
.stButton > button, .stDownloadButton > button {{ background:var(--cip-button-secondary-bg) !important; color:var(--cip-button-secondary-text) !important; border-radius: 14px; border: 1px solid var(--cip-border); min-height: 2.6rem; font-weight: 750; opacity:1 !important; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ background:var(--cip-nav-hover-bg) !important; border-color: var(--cip-accent); color: var(--cip-text) !important; }}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{ background:var(--cip-button-primary-bg) !important; color:var(--cip-button-primary-text) !important; border-color:var(--cip-button-primary-bg) !important; }}
div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="textarea"], textarea {{ background:var(--cip-input-bg) !important; color:var(--cip-input-text) !important; border-radius: 14px !important; border-color:var(--cip-border) !important; }}
div[data-baseweb="input"] input, div[data-baseweb="select"] input, textarea, input {{ color:var(--cip-input-text) !important; -webkit-text-fill-color:var(--cip-input-text) !important; }}
div[data-baseweb="select"] span, div[data-baseweb="select"] div, div[data-baseweb="popover"] * {{ color:var(--cip-input-text) !important; }}
div[data-baseweb="popover"] div {{ background:var(--cip-elevated) !important; }}
input::placeholder, textarea::placeholder {{ color:var(--cip-muted) !important; opacity:1 !important; }}
[data-testid="stRadio"] label, [data-testid="stFileUploader"] label, [data-testid="stTextInput"] label, [data-testid="stTextArea"] label, [data-testid="stSelectbox"] label {{ color:var(--cip-text) !important; }}
.streamlit-expanderHeader, [data-testid="stExpander"] details summary, [data-testid="stExpander"] * {{ color:var(--cip-text) !important; }}
[aria-disabled="true"], button:disabled {{ opacity:.55 !important; color:var(--cip-muted) !important; }}
.cip-shell-topbar {{ display:flex; align-items:center; justify-content:space-between; gap:1rem; background:var(--cip-surface); border:1px solid var(--cip-border); border-radius:24px; padding:1rem 1.15rem; margin:.25rem 0 1.1rem; box-shadow:var(--cip-shadow); }}
.cip-page-title h1 {{ margin:0; color:var(--cip-text); font-size:2rem; letter-spacing:-.04em; }}
.cip-page-title p {{ margin:.25rem 0 0; color:var(--cip-muted); line-height:1.55; }}
.cip-brand-card {{ background:linear-gradient(135deg,var(--cip-surface),var(--cip-accent-soft)); border:1px solid var(--cip-border-strong); border-radius:24px; padding:1rem; margin:.5rem 0 1rem; box-shadow:var(--cip-shadow); }}
.cip-brand-title {{ font-size:1.05rem; font-weight:900; color:var(--cip-text); }}
.cip-brand-subtitle, .cip-muted {{ color: var(--cip-muted); }}
.cip-nav-group {{ color:var(--cip-muted); font-size:.72rem; font-weight:900; letter-spacing:.1em; text-transform:uppercase; margin:1.1rem 0 .35rem; }}
.cip-nav-active {{ background:var(--cip-nav-active-bg); border:1px solid var(--cip-nav-active-bg); color:var(--cip-nav-active-text) !important; border-radius:16px; padding:.65rem .75rem; font-weight:900; margin:.2rem 0; text-align:{align}; }}
.rtl {{ direction:rtl; text-align:right; }}
.ltr-value, .technical-value {{ direction:ltr; unicode-bidi:isolate; display:inline-block; }}
.cip-auth-card, .cip-card, .cip-kpi, .cip-review-card, .cip-risk-card, .cip-missing-card, .cip-summary-card, .cip-error-card, .cip-action-card, .cip-benchmark-card, .cip-status-card, .cip-empty-state {{ background:var(--cip-card); border:1px solid var(--cip-border); border-radius:22px; box-shadow:var(--cip-shadow); color:var(--cip-text); }}
.cip-auth-card {{ padding:1rem 1.15rem; }}
.cip-card {{ padding:1.3rem; }}
.cip-hero {{ padding:1.4rem 1.6rem; border-radius:26px; color:var(--cip-text); background:linear-gradient(135deg,var(--cip-surface),var(--cip-accent-soft)); border:1px solid var(--cip-border-strong); }}
.cip-pill {{ display:inline-flex; padding:.25rem .7rem; border-radius:999px; background:var(--cip-text); color:var(--cip-surface-strong); font-size:.78rem; }}
.cip-kpi {{ min-height:118px; padding:1rem; }}
.cip-kpi-label {{ color:var(--cip-muted); font-size:.76rem; font-weight:800; letter-spacing:.04em; text-transform:uppercase; }}
.cip-kpi-value {{ color:var(--cip-text); font-size:1.65rem; line-height:1.15; font-weight:900; margin-top:.35rem; }}
.cip-kpi-detail {{ color:var(--cip-muted); font-size:.86rem; margin-top:.35rem; }}
.cip-review-card, .cip-risk-card, .cip-missing-card, .cip-summary-card, .cip-error-card {{ padding:1.1rem 1.2rem; margin:.75rem 0; }}
.cip-risk-card {{ border-{align}:5px solid #f97316; }}
.cip-missing-card, .cip-error-card {{ border-{align}:5px solid #ef4444; }}
.cip-summary-card {{ color:var(--cip-text); font-size:1rem; line-height:1.65; }}
.cip-card-header {{ display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; }}
.cip-card-header h3, .cip-card-header h4 {{ margin:.1rem 0 .35rem 0; color:var(--cip-text); }}
.cip-card-meta {{ display:flex; flex-wrap:wrap; gap:.5rem; margin:.65rem 0 .85rem 0; color:var(--cip-muted); }}
.cip-card-meta span {{ background:var(--cip-surface); border:1px solid var(--cip-border); border-radius:999px; padding:.22rem .55rem; font-size:.82rem; }}
.cip-eyebrow {{ color:var(--cip-muted); font-size:.72rem; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }}
.cip-badge {{ display:inline-flex; align-items:center; border-radius:999px; padding:.28rem .62rem; font-weight:900; font-size:.74rem; white-space:nowrap; }}
.cip-badge-green {{ color:var(--cip-success-text); background:var(--cip-success-bg); border:1px solid rgba(34,197,94,.45); }}
.cip-badge-amber {{ color:var(--cip-warning-text); background:var(--cip-warning-bg); border:1px solid rgba(245,158,11,.45); }}
.cip-badge-red {{ color:var(--cip-danger-text); background:var(--cip-danger-bg); border:1px solid rgba(239,68,68,.45); }}
.cip-badge-blue {{ color:var(--cip-accent-text); background:var(--cip-accent-soft); border:1px solid var(--cip-border-strong); }}
.cip-evidence {{ background:var(--cip-surface); border:1px solid var(--cip-border-strong); border-radius:18px; padding:.85rem 1rem; margin:.45rem 0; }}
.cip-evidence-meta {{ color:var(--cip-muted); font-size:.78rem; font-weight:800; margin-bottom:.35rem; }}
.cip-evidence blockquote {{ margin:.25rem 0 0 0; padding-{align}:.85rem; border-{align}:4px solid var(--cip-accent); color:var(--cip-text); line-height:1.55; }}
.cip-recommendation, .cip-check-item {{ background:var(--cip-success-bg); border:1px solid rgba(34,197,94,.45); color:var(--cip-success-text); border-radius:16px; padding:.8rem 1rem; margin:.55rem 0; }}
.cip-ai-box {{ background:var(--cip-accent-soft); border:1px solid var(--cip-border-strong); color:var(--cip-accent-text); border-radius:16px; padding:.85rem 1rem; margin:.55rem 0; line-height:1.55; }}
.cip-layman-box {{ background:linear-gradient(135deg,var(--cip-accent-soft),var(--cip-card)); border:1px solid var(--cip-border-strong); border-radius:20px; padding:1.05rem 1.15rem; margin:.7rem 0; font-size:1.04rem; line-height:1.75; color:var(--cip-text); }}
.cip-negotiation, .cip-risk-chip {{ background:var(--cip-warning-bg); border:1px solid rgba(245,158,11,.45); color:var(--cip-warning-text); border-radius:16px; padding:.85rem 1rem; margin:.55rem 0; }}
.cip-assistant-bubble {{ background:var(--cip-card); border:1px solid var(--cip-border-strong); border-radius:20px; padding:1rem 1.1rem; box-shadow:var(--cip-shadow); line-height:1.62; }}
.cip-chat-contract {{ background:var(--cip-accent-soft); border:1px solid var(--cip-border-strong); color:var(--cip-accent-text); border-radius:18px; padding:.85rem 1rem; margin:.4rem 0 1rem 0; }}
.cip-suggestion-chip {{ display:inline-flex; background:var(--cip-surface); border:1px solid var(--cip-border); color:var(--cip-text); border-radius:999px; padding:.42rem .7rem; margin:.25rem; font-size:.86rem; }}
.cip-action-card {{ border-left:5px solid #22c55e; padding:1rem 1.1rem; margin:.7rem 0; }}
.cip-score-meter {{ background:var(--cip-card); border:1px solid var(--cip-border); border-radius:22px; padding:1.25rem; box-shadow:var(--cip-shadow); }}
.cip-score-value {{ font-size:2.75rem; font-weight:950; color:var(--cip-text); letter-spacing:-.05em; }}
.cip-score-track {{ height:14px; border-radius:999px; background:var(--cip-border); overflow:hidden; margin:.85rem 0 .55rem; }}
.cip-score-fill {{ display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,#ef4444,#f59e0b,#22c55e); }}
.cip-benchmark-card {{ padding:1rem 1.1rem; margin:.7rem 0; }}
.cip-mini-bar {{ height:10px; border-radius:999px; background:var(--cip-border); overflow:hidden; margin:.35rem 0 .8rem; }}
.cip-mini-bar span {{ display:block; height:100%; background:linear-gradient(90deg,#ef4444,#f59e0b,#22c55e); }}
.cip-status-card {{ padding:1rem 1.1rem; margin:.65rem 0; min-height:150px; }}
.cip-endpoint-row {{ display:grid; grid-template-columns: minmax(160px,1.2fr) auto auto minmax(220px,2fr); gap:.75rem; align-items:center; background:var(--cip-card); border:1px solid var(--cip-border); border-radius:16px; padding:.8rem 1rem; margin:.5rem 0; color:var(--cip-text); }}
.cip-empty-state {{ padding:1.25rem; text-align:center; color:var(--cip-muted); margin:1rem 0; }}
@media (max-width: 760px) {{ .cip-endpoint-row, .cip-shell-topbar {{ grid-template-columns: 1fr; display:block; }} .block-container {{ padding-left:.75rem; padding-right:.75rem; }} }}
</style>
"""


APP_CSS = build_app_css("light", "ltr")
