import streamlit as st
import requests
import os
import sys
import html
import json
from pathlib import Path
from typing import Any, Dict
import pandas as pd
import fitz  # PyMuPDF

# Streamlit executes this file from /app/frontend in Docker, so make the
# repository root importable before loading the frontend package modules.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from frontend.components.alerts import empty_state, friendly_error
from frontend.components.cards import metric_card, section_card
from frontend.components.clause_cards import render_clause_card
from frontend.components.layout import page_header, topbar, workflow_stepper
from frontend.components.readiness_review import render_readiness_review
from frontend.services.api_client import request_api
from frontend.services.formatters import titleize_key
from frontend.services.reporting import build_professional_report_pdf
from frontend.services.state import clear_session, init_session_state, select_contract
from frontend.styles.global_css import apply_global_css



def render_brand_logo(subtitle: str | None = None) -> None:
    subtitle_html = f"<div class='brand-subtitle'>{html.escape(subtitle)}</div>" if subtitle else ""
    st.markdown(
        f"""
        <div class='brand-lockup'>
            <div class='brand-mark'>CI</div>
            <div>
                <div class='brand-name'>Contract Intelligence</div>
                {subtitle_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_next_step(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class='next-step-card'>
            <strong>{html.escape(title)}</strong><br/>
            <span>{html.escape(body)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
BENCHMARK_ENABLED = os.getenv("BENCHMARK_ENABLED", "true").lower() == "true"

# Initialize session state
init_session_state()


def apply_modern_theme(sidebar_compact: bool = False):
    sidebar_width = "5.2rem" if sidebar_compact else "19.5rem"
    sidebar_text_display = "none" if sidebar_compact else "block"

    st.markdown(
        f"""
        <style>
        /* ==================== Design System ==================== */
        .stApp {{
            background: radial-gradient(circle at 12% 20%, rgba(125, 95, 255, 0.14), transparent 42%),
                        radial-gradient(circle at 82% 12%, rgba(51, 96, 255, 0.14), transparent 42%),
                        linear-gradient(140deg, #eef3f8 0%, #e8eef6 46%, #eaf2f6 100%);
            font-family: Inter, "SF Pro Text", "Segoe UI", sans-serif;
            animation: pageFadeIn 0.45s ease-out;
        }}
        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            background: linear-gradient(130deg, rgba(98, 86, 255, 0.06), rgba(67, 116, 255, 0.05), rgba(88, 168, 255, 0.05));
            background-size: 190% 190%;
            animation: gradientShift 14s ease-in-out infinite;
            pointer-events: none;
            z-index: 0;
        }}
        .block-container {{
            position: relative;
            z-index: 1;
            padding-top: 1.1rem;
            padding-bottom: 2.2rem;
            animation: fadeInUp 0.35s ease-out;
        }}
        @keyframes gradientShift {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        @keyframes pageFadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ==================== Typography & Layout ==================== */
        h1, h2, h3 {{
            color: #1d2438;
            letter-spacing: -0.02em;
            font-weight: 760;
        }}
        .page-transition {{
            animation: fadeInUp 0.28s ease-in-out;
        }}

        /* ==================== Sidebar ==================== */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #121b36 0%, #1b2342 45%, #1f2748 100%);
            border-right: 1px solid rgba(156, 173, 211, 0.25);
            box-shadow: 10px 0 40px rgba(12, 18, 35, 0.28);
            min-width: {sidebar_width} !important;
            max-width: {sidebar_width} !important;
            transition: all 0.28s ease-in-out;
        }}
        section[data-testid="stSidebar"] * {{
            color: #e9f0ff !important;
            transition: all 0.25s ease-in-out;
        }}
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{ display: none; }}
        section[data-testid="stSidebar"] .stCaption,
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] p {{
            display: {sidebar_text_display};
        }}
        section[data-testid="stSidebar"] div[role="radiogroup"] label {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(173, 196, 255, 0.25);
            border-radius: 12px;
            margin-bottom: 0.45rem;
            padding: 0.45rem 0.5rem;
            transition: all 0.25s ease-in-out;
        }}
        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
            transform: translateX(2px);
            background: rgba(111, 135, 255, 0.22);
            border-color: rgba(178, 197, 255, 0.55);
            box-shadow: 0 8px 22px rgba(28, 43, 87, 0.35);
        }}
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
            background: linear-gradient(90deg, rgba(74, 105, 255, 0.35), rgba(137, 94, 255, 0.35));
            border-color: rgba(198, 210, 255, 0.72);
            box-shadow: 0 8px 22px rgba(53, 73, 132, 0.34);
        }}

        /* ==================== Components ==================== */
        div[data-testid="stTabs"] button {{
            border-radius: 12px 12px 0 0;
            background: transparent;
            color: #2b3552;
            font-weight: 700;
            border: none;
            transition: all 0.22s ease-in-out;
        }}
        div[data-testid="stTabs"] button[aria-selected="true"] {{
            background: linear-gradient(90deg, #233155 0%, #2f3f67 100%) !important;
            color: #ffffff !important;
        }}
        div[data-testid="stForm"], div[data-testid="stExpander"] {{
            background: rgba(255, 255, 255, 0.55);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(205, 221, 247, 0.75);
            border-radius: 16px;
            padding: 0.65rem;
            box-shadow: 0 14px 36px rgba(33, 45, 77, 0.09);
            transition: all 0.3s ease;
        }}
        div[data-testid="stTextInputRootElement"],
        div[data-testid="stTextAreaRootElement"],
        div[data-baseweb="select"] > div {{
            border-radius: 12px !important;
            transition: all 0.24s ease-in-out !important;
        }}
        div[data-testid="stTextInputRootElement"]:focus-within,
        div[data-testid="stTextAreaRootElement"]:focus-within {{
            box-shadow: 0 0 0 3px rgba(92, 122, 255, 0.22) !important;
            border-color: rgba(92, 122, 255, 0.6) !important;
        }}
        .stButton > button,
        .stForm [data-testid="stFormSubmitButton"] button {{
            border-radius: 12px;
            border: 1px solid #364976;
            background: linear-gradient(100deg, #24335e 0%, #3a4f89 100%);
            color: white;
            font-weight: 700;
            box-shadow: 0 9px 24px rgba(26, 39, 70, 0.28);
            transition: all 0.28s ease-in-out;
        }}
        .stButton > button:hover,
        .stForm [data-testid="stFormSubmitButton"] button:hover {{
            transform: translateY(-2px) scale(1.01);
            box-shadow: 0 14px 30px rgba(33, 48, 87, 0.35);
            filter: brightness(1.03);
        }}

        /* ==================== Reusable Cards ==================== */
        .metric-card {{
            background: rgba(255, 255, 255, 0.56);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(201, 216, 244, 0.8);
            border-radius: 16px;
            padding: 0.95rem 1rem;
            box-shadow: 0 14px 35px rgba(30, 43, 74, 0.10);
            transition: all 0.28s ease-in-out;
        }}
        .metric-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 18px 36px rgba(30, 43, 74, 0.16);
            border-color: rgba(134, 159, 255, 0.65);
        }}
        .metric-label {{
            font-size: 0.81rem;
            color: #667291;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.3rem;
        }}
        .metric-value {{
            font-size: 1.45rem;
            color: #1f2b49;
            font-weight: 760;
            line-height: 1.1;
        }}
        .metric-sub {{
            color: #667291;
            font-size: 0.82rem;
            margin-top: 0.2rem;
        }}

        .topbar {{
            background: rgba(255, 255, 255, 0.5);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(201, 216, 244, 0.8);
            border-radius: 16px;
            padding: 0.88rem 1rem;
            margin-bottom: 0.85rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 14px 34px rgba(30, 43, 74, 0.1);
        }}
        .topbar-title {{
            font-weight: 800;
            color: #1f2a45;
            letter-spacing: 0.02em;
        }}
        .topbar-sub {{
            color: #5d6883;
            font-size: 0.9rem;
        }}

        .login-wrap {{
            width: 100%;
            display: block;
            animation: fadeInUp 0.35s ease-out;
        }}
        .login-card {{
            width: min(760px, 96vw);
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.56);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(191, 209, 241, 0.75);
            border-radius: 18px;
            padding: 1.25rem 1.25rem 0.55rem;
            box-shadow: 0 20px 45px rgba(25, 38, 70, 0.16);
        }}

        .chat-shell {{
            background: rgba(255, 255, 255, 0.55);
            border: 1px solid #d8e1e8;
            border-radius: 16px;
            padding: 1rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
        }}
        .chat-scroll {{
            max-height: 360px;
            overflow-y: auto;
            padding-right: 0.25rem;
            margin-bottom: 0.5rem;
        }}
        .chat-row {{ display: flex; margin: 0.5rem 0; }}
        .chat-row.user {{ justify-content: flex-end; }}
        .chat-bubble {{
            max-width: 86%;
            padding: 0.7rem 0.9rem;
            border-radius: 14px;
            border: 1px solid #dce4ec;
            line-height: 1.45;
            font-size: 0.98rem;
            transition: all 0.22s ease;
        }}
        .chat-bubble.assistant {{
            background: #ffffff;
            color: #222b3c;
            border-top-left-radius: 6px;
            box-shadow: 0 2px 10px rgba(30, 44, 75, 0.08);
        }}
        .chat-bubble.user {{
            background: linear-gradient(140deg, #25304f 0%, #37476f 100%);
            color: #ffffff;
            border-color: #293558;
            border-top-right-radius: 6px;
            box-shadow: 0 4px 14px rgba(31, 41, 68, 0.24);
        }}

        .fab-chip {{
            position: fixed;
            right: 1.4rem;
            bottom: 1.3rem;
            background: linear-gradient(120deg, #2b3f79 0%, #5b48b8 100%);
            color: #fff;
            border-radius: 999px;
            padding: 0.62rem 0.9rem;
            box-shadow: 0 16px 26px rgba(35, 43, 93, 0.35);
            border: 1px solid rgba(213, 226, 255, 0.24);
            font-size: 0.82rem;
            font-weight: 600;
            z-index: 1000;
            pointer-events: none;
            opacity: 0.95;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_dashboard_stats() -> Dict:
    """Fetch real dashboard stats from backend APIs."""
    stats = {
        "total_requests": "—",
        "success_rate": "—",
        "clients": "—",
        "contracts": "—",
    }

    metrics_response = make_api_request("/metrics")
    if metrics_response and metrics_response.status_code == 200:
        metrics = metrics_response.json()
        stats["total_requests"] = metrics.get("total_requests", "—")
        success_rate = metrics.get("success_rate")
        stats["success_rate"] = (
            f"{success_rate:.1f}%" if isinstance(success_rate, (int, float)) else "—"
        )

    clients_response = make_api_request("/clients")
    if clients_response and clients_response.status_code == 200:
        stats["clients"] = len(clients_response.json().get("clients", []))

    contracts_response = make_api_request("/contracts")
    if contracts_response and contracts_response.status_code == 200:
        stats["contracts"] = len(contracts_response.json().get("contracts", []))

    return stats


def render_metric_card(title: str, value: str, subtitle: str = ""):
    metric_card(title, value, subtitle)


def get_ai_status_label() -> str:
    response, _ = request_api(API_BASE_URL, "/llm/health", method="GET", timeout=8)
    if response and response.status_code == 200:
        return "Online" if response.json().get("reachable") else "Offline"
    return "Checking"


def get_header_stats() -> Dict[str, Any]:
    """Load lightweight header metrics without surfacing API failures in the main UI."""
    stats: Dict[str, Any] = {
        "total_requests": 0,
        "success_rate": "N/A",
        "clients": 0,
        "contracts": 0,
        "analyzed_contracts": 0,
    }

    token = st.session_state.get("token")
    metrics_response, _ = request_api(API_BASE_URL, "/metrics", method="GET", token=token, timeout=8)
    if metrics_response and metrics_response.status_code == 200:
        metrics = metrics_response.json()
        stats["total_requests"] = metrics.get("total_requests", 0) or 0
        success_rate = metrics.get("success_rate")
        stats["success_rate"] = f"{success_rate:.1f}%" if isinstance(success_rate, (int, float)) else "N/A"

    clients_response, _ = request_api(API_BASE_URL, "/clients", method="GET", token=token, timeout=8)
    if clients_response and clients_response.status_code == 200:
        stats["clients"] = len(clients_response.json().get("clients", []))

    contracts_response, _ = request_api(API_BASE_URL, "/contracts", method="GET", token=token, timeout=8)
    if contracts_response and contracts_response.status_code == 200:
        contracts = contracts_response.json().get("contracts", [])
        stats["contracts"] = len(contracts)
        stats["analyzed_contracts"] = sum(1 for contract in contracts if contract.get("status") == "analyzed")

    return stats


def render_chrome_header(username: str, stats: Dict[str, Any] | None = None):
    selected_contract = st.session_state.get("current_contract_title") or st.session_state.get("selected_contract_id") or "No contract selected"
    topbar(username, ai_status=get_ai_status_label(), selected_contract=str(selected_contract))

    header_stats = {
        "total_requests": 0,
        "success_rate": "N/A",
        "clients": 0,
        "analyzed_contracts": 0,
        **(stats or get_header_stats()),
    }

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Total Requests", str(header_stats.get("total_requests", 0)), "All tracked API calls")
    with c2:
        render_metric_card("Success Rate", str(header_stats.get("success_rate", "N/A")), "Healthy backend responses")
    with c3:
        render_metric_card("Clients", str(header_stats.get("clients", 0)), "Managed organizations")
    with c4:
        render_metric_card("Analyzed Contracts", str(header_stats.get("analyzed_contracts", 0)), "Ready for review")


def make_api_request(
    endpoint: str,
    method: str = "GET",
    data: Dict = None,
    files: Dict = None,
    auth: bool = True,
):
    """Compatibility wrapper around the shared frontend API client."""
    token = st.session_state.token if auth else None
    response, api_error = request_api(
        API_BASE_URL,
        endpoint,
        method=method,
        token=token,
        data=data,
        files=files,
    )
    st.session_state.last_api_error = api_error

    if response is not None and response.status_code == 401:
        st.session_state.token = None
        st.session_state.username = None
        friendly_error(
            "Your session expired. Please sign in again.",
            "Sign in to continue using your workspace.",
            api_error.technical_detail if api_error else None,
        )
        st.rerun()

    if response is None and api_error:
        friendly_error(api_error.friendly_message, api_error.suggested_next_step, api_error.technical_detail)
    return response


def extract_text_from_uploaded_pdf(pdf_bytes: bytes) -> str:
    """Extract text from uploaded PDF bytes for contract persistence."""
    text = ""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf_doc:
            for page in pdf_doc:
                text += page.get_text()
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {str(e)}") from e

    if not text.strip():
        raise ValueError(
            "Could not extract text from this PDF. If it is scanned/image-only, please use OCR-enabled analysis first."
        )

    return text


def render_contract_evaluation(evaluation: Dict):
    render_readiness_review(evaluation)


def build_pipeline_report_pdf(contract_title: str, report_payload: Dict[str, Any], client_name: str | None = None) -> bytes:
    return build_professional_report_pdf(
        contract_title,
        report_payload,
        client_name=client_name or st.session_state.get("selected_client_name", "Not specified"),
        report_title="Contract Review Report",
    )


def render_chat_history(chat_messages):
    if not chat_messages:
        st.markdown(
            """
            <div class='chat-shell'>
                <h3 style='margin:0 0 .25rem 0;'>Ask anything about this contract</h3>
                <p style='margin:0;color:#5a6578;'>I can help you find clauses, explain risks, summarize obligations, and identify missing terms.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown("<div class='chat-shell'><div class='chat-scroll'>", unsafe_allow_html=True)
    for idx, msg in enumerate(chat_messages):
        role = msg.get("role", "assistant")
        role_class = "user" if role == "user" else "assistant"
        escaped_text = html.escape(msg.get("content", ""))
        escaped_text = escaped_text.replace("\n", "<br>")
        st.markdown(
            f"""
            <div class='chat-row {role_class}'>
                <div class='chat-bubble {role_class}'>{escaped_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        evidence = msg.get("evidence_snippets") or []
        if role != "user" and evidence:
            with st.expander(f"Evidence for assistant response {idx + 1}"):
                for ev in evidence:
                    st.markdown(f"**{ev.get('clause_name', 'Evidence')}** — {ev.get('relevance', 'Relevant evidence')}")
                    st.info(ev.get("quote", ""))
                    if ev.get("location"):
                        st.caption(ev.get("location"))
    st.markdown("</div></div>", unsafe_allow_html=True)


def login_page():
    """Premium Login and Registration page."""
    st.markdown("<div class='auth-shell'><div class='auth-card'>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='auth-hero'>
            <div>
                <div class='brand-lockup'>
                    <div class='brand-mark'>CI</div>
                    <div>
                        <div class='brand-name' style='color:#fff;'>Contract Intelligence</div>
                        <div class='brand-subtitle' style='color:rgba(255,255,255,.78);'>AI contract review workspace</div>
                    </div>
                </div>
                <h1>Review contracts with confidence.</h1>
                <p>Upload contracts, review clauses, benchmark terms, and ask evidence-based AI questions in one clean workspace.</p>
            </div>
            <div class='trust-list'>
                <div class='trust-item'>✓ AI-powered clause review</div>
                <div class='trust-item'>✓ Evidence-based answers</div>
                <div class='trust-item'>✓ Private by default</div>
            </div>
        </div>
        <div class='auth-panel'>
        """,
        unsafe_allow_html=True,
    )
    render_brand_logo("Secure workspace for contract review")

    tab1, tab2 = st.tabs(["Sign in", "Create account"])

    with tab1:
        st.markdown("### Welcome back")
        st.caption("Sign in to your workspace.")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit = st.form_submit_button("Sign in")

            if submit:
                if not username.strip() or not password:
                    st.error("Please enter your username and password.")
                else:
                    response = make_api_request(
                        "/auth/login",
                        "POST",
                        {"username": username.strip(), "password": password},
                        auth=False,
                    )

                    if response and response.status_code == 200:
                        data = response.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.username = username.strip()
                        st.success("Signed in successfully.")
                        st.rerun()
                    else:
                        api_error = st.session_state.get("last_api_error")
                        if api_error and api_error.status_code is None:
                            friendly_error(api_error.friendly_message, api_error.suggested_next_step, api_error.technical_detail)
                        else:
                            st.error("We could not sign you in. Please check your username and password.")
        st.caption("New here? Create an account using the tab beside Sign in.")

    with tab2:
        st.markdown("### Create your workspace")
        st.caption("Start analyzing contracts with AI-powered insights.")
        with st.form("register_form"):
            username = st.text_input("Username", placeholder="Choose a username", key="register_username")
            email = st.text_input("Email", placeholder="name@company.com", key="register_email")
            password = st.text_input("Password", type="password", placeholder="Use at least 8 characters", key="register_password")
            confirm_password = st.text_input("Confirm password", type="password", placeholder="Re-enter your password", key="register_confirm_password")
            st.caption("Use at least 8 characters. Choose something you do not use elsewhere.")
            submit = st.form_submit_button("Create account")

            if submit:
                if not username.strip():
                    st.error("Please enter a username.")
                elif not email.strip():
                    st.error("Please enter an email address.")
                elif not password:
                    st.error("Please enter a password.")
                elif len(password) < 8:
                    st.error("Please use a password with at least 8 characters.")
                elif password != confirm_password:
                    st.error("Passwords do not match. Please re-enter them.")
                else:
                    response = make_api_request(
                        "/auth/register",
                        "POST",
                        {"username": username.strip(), "email": email.strip(), "password": password},
                        auth=False,
                    )

                    if response and response.status_code == 200:
                        st.success("Account created. You can now sign in.")
                        st.caption("Already have an account? Sign in using the tab above.")
                    else:
                        api_error = st.session_state.get("last_api_error")
                        if api_error and api_error.status_code is None:
                            friendly_error(api_error.friendly_message, api_error.suggested_next_step, api_error.technical_detail)
                        else:
                            st.error("That username or email may already be registered.")
        st.caption("Already have an account? Sign in using the tab above.")

    st.markdown("</div></div></div>", unsafe_allow_html=True)


def get_clients_list():
    """Get list of all clients for the current user"""
    response = make_api_request("/clients")
    if response and response.status_code == 200:
        return response.json().get("clients", [])
    return []


def contract_analysis_page():
    """Guided Contract Analysis page."""
    page_header("Analyze", "Upload a contract, extract key clauses, review health, compare benchmarks, and ask AI questions from one guided workflow.", "Contract workflow")
    workflow_stepper(["Select client", "Upload contract", "Run analysis", "Review health", "Compare benchmark", "Ask AI"], active_index=2 if st.session_state.get("current_clauses") else 1)
    render_next_step("Next step", "Select or create a client, upload a PDF contract, then choose Analyze Contract Clauses.")
    
    # Display extended success message for client creation
    if "client_creation_success" in st.session_state:
        import time
        success_data = st.session_state.client_creation_success
        # Show message for 10 seconds
        if time.time() - success_data["timestamp"] < 10:
            st.success(success_data["message"])
        else:
            # Remove expired message
            del st.session_state.client_creation_success

    st.header("Client Management")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Create New Client")
        with st.form("client_form"):
            client_name = st.text_input("Client Name")
            client_email = st.text_input("Client Email")
            client_phone = st.text_input("Client Phone (optional)")
            submit_client = st.form_submit_button("Create Client")

            if submit_client and client_name and client_email:
                response = make_api_request(
                    "/clients",
                    "POST",
                    {
                        "name": client_name,
                        "email": client_email,
                        "phone": client_phone if client_phone else None,
                    },
                )

                if response and response.status_code == 200:
                    data = response.json()
                    client_id = data.get("client_id")
                    st.success(f"Client '{client_name}' created successfully!")
                    st.info(f"Client ID: {client_id}")
                    # Store success message with timestamp for extended display
                    st.session_state.client_creation_success = {
                        "message": f"Client '{client_name}' created successfully! Client ID: {client_id}",
                        "timestamp": __import__('time').time()
                    }
                    # Automatically select the newly created client
                    st.session_state.selected_client_id = client_id
                    st.session_state.selected_client_name = client_name
                    st.rerun()
                else:
                    error_msg = "Failed to create client"
                    if response:
                        try:
                            error_data = response.json()
                            error_msg = error_data.get("detail", error_msg)
                        except:
                            pass
                    st.error(error_msg)

    with col2:
        st.subheader("Select Existing Client")
        
        # Get list of existing clients
        clients = get_clients_list()
        
        if clients:
            # Create options for selectbox
            client_options = {}
            for client in clients:
                client_id = client.get("_id") or client.get("id")
                client_name = client.get("name", "Unknown")
                client_email = client.get("email", "")
                display_name = f"{client_name} ({client_email})"
                client_options[display_name] = {
                    "id": client_id,
                    "name": client_name
                }
            
            # Add "None" option at the beginning
            options = ["-- Select a client --"] + list(client_options.keys())
            
            selected_option = st.selectbox(
                "Choose from existing clients:",
                options,
                key="client_selector"
            )
            
            if selected_option and selected_option != "-- Select a client --":
                client_info = client_options[selected_option]
                st.session_state.selected_client_id = client_info["id"]
                st.session_state.selected_client_name = client_info["name"]
                st.success(f"Selected: {client_info['name']}")
        else:
            st.info("No existing clients found. Create a new client above.")
            

    if "selected_client_id" in st.session_state:
        st.header("Contract Management")

        client_id = st.session_state.selected_client_id

        # Show existing contracts for this client
        contracts_response = make_api_request(f"/clients/{client_id}/contracts")
        if contracts_response and contracts_response.status_code == 200:
            contracts = contracts_response.json()["contracts"]

            if contracts:
                st.subheader("Existing Contracts")
                for contract in contracts:
                    contract_id = contract.get('_id', 'N/A')
                    contract_title = contract.get('title', 'Untitled')
                    with st.expander(f"Contract: {contract_title}"):
                        st.write(f"**ID:** {contract_id}")
                        st.write(f"**Status:** {contract.get('status', 'N/A')}")
                        st.write(f"**Created:** {contract.get('created_at', 'N/A')}")

                        if st.button("Use This Contract for AI Analysis", key=f"use_contract_{contract_id}"):
                            st.session_state.current_contract_id = contract_id
                            st.session_state.current_contract_title = contract_title
                            st.session_state.current_contract_content = contract.get("content", "")
                            if "current_pdf_bytes" in st.session_state:
                                del st.session_state.current_pdf_bytes
                            if "current_clauses" in st.session_state:
                                del st.session_state.current_clauses
                            st.success(f"Loaded contract '{contract_title}' for AI analysis")
                            st.rerun()

        # Create new contract
        st.subheader("Create New Contract")
        with st.form("contract_form"):
            contract_title = st.text_input("Contract Title")
            uploaded_file = st.file_uploader("Upload Contract PDF", type="pdf")
            submit_contract = st.form_submit_button("Create Contract")

            if submit_contract and contract_title and uploaded_file:
                # Validate file type
                if not uploaded_file.name.lower().endswith('.pdf'):
                    st.error("Please upload a PDF file")
                    return
                
                # First, extract text from PDF
                try:
                    pdf_bytes = uploaded_file.read()
                    contract_content = extract_text_from_uploaded_pdf(pdf_bytes)

                    # Create contract
                    response = make_api_request(
                        "/contracts",
                        "POST",
                        {
                            "title": contract_title,
                            "client_id": client_id,
                            "content": contract_content,
                        },
                    )

                    if response and response.status_code == 200:
                        contract_data = response.json()
                        contract_id = contract_data["contract_id"]
                        st.success(f"Contract '{contract_title}' created successfully!")
                        st.info(f"Contract ID: {contract_id}")

                        # Store for analysis
                        st.session_state.current_contract_id = contract_id
                        st.session_state.current_pdf_bytes = pdf_bytes
                        st.session_state.current_contract_content = contract_content
                        st.session_state.current_contract_title = contract_title
                        st.rerun()
                    else:
                        error_msg = "Failed to create contract"
                        if response:
                            try:
                                error_data = response.json()
                                error_msg = error_data.get("detail", error_msg)
                            except:
                                pass
                        st.error(error_msg)
                except Exception as e:
                    st.error(f"Error processing PDF: {str(e)}")
            elif submit_contract:
                if not contract_title:
                    st.error("Please enter a contract title")
                if not uploaded_file:
                    st.error("Please upload a PDF file")

    else:
        st.info("Please create or select a client first to proceed with contract management")
        
        # Add button to clear selection if needed
        if "selected_client_id" in st.session_state:
            if st.button("Clear Client Selection"):
                if "selected_client_id" in st.session_state:
                    del st.session_state.selected_client_id
                if "selected_client_name" in st.session_state:
                    del st.session_state.selected_client_name
                st.rerun()

    if "current_contract_id" in st.session_state:
        st.header("AI Contract Analysis")

        contract_id = st.session_state.current_contract_id
        pdf_bytes = st.session_state.get("current_pdf_bytes")
        contract_content = st.session_state.get("current_contract_content", "")
        contract_title = st.session_state.get("current_contract_title", "Unknown")
        
        # Show contract being analyzed
        st.info(f"Analyzing contract: **{contract_title}** (ID: {contract_id})")
        if not pdf_bytes:
            st.info("Using saved contract content from database (no re-upload needed).")

        response_language = st.selectbox(
            "Response Language / لغة الاستجابة",
            options=["english", "arabic"],
            format_func=lambda x: "English" if x == "english" else "العربية",
            key="response_language_selector",
        )
        use_ocr = st.toggle("Enable OCR for scanned PDFs (English + Arabic)", value=True)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Analyze Contract Clauses"):
                st.session_state.pop("current_clauses", None)
                with st.spinner("Analyzing contract clauses..."):
                    if pdf_bytes:
                        files = {"file": ("contract.pdf", pdf_bytes, "application/pdf")}
                        response = make_api_request(
                            "/genai/analyze-contract",
                            "POST",
                            data={"response_language": response_language, "use_ocr": use_ocr},
                            files=files,
                        )
                    elif contract_content:
                        response = make_api_request(
                            "/genai/analyze-contract-text",
                            "POST",
                            {"contract_text": contract_content, "response_language": response_language},
                        )
                    else:
                        response = None
                        st.error("This contract has no stored content to analyze.")

                    if response and response.status_code == 200:
                        data = response.json()
                        structured = data.get("structured_clauses", {})
                        clauses = structured.get("clauses", {})
                        clause_explanations = data.get("clause_explanations", {})

                        st.success("Contract analyzed successfully!")
                        found_count = sum(1 for v in clauses.values() if isinstance(v, dict) and v.get("status") == "found")
                        not_found_count = sum(1 for v in clauses.values() if isinstance(v, dict) and v.get("status") in {"not_found", "missing"})
                        review_count = max(0, len(clauses) - found_count - not_found_count)
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Clauses Found", found_count)
                        m2.metric("Need Review", review_count)
                        m3.metric("Not Found", not_found_count)

                        st.subheader("Validated Clause Extraction")
                        filter_col, search_col = st.columns([1, 2])
                        with filter_col:
                            clause_filter = st.selectbox("Filter clauses", ["All", "Found", "Needs Review", "Not Found"], key=f"clause_filter_{contract_id}")
                        with search_col:
                            clause_search = st.text_input("Search clauses", placeholder="Search by clause name...", key=f"clause_search_{contract_id}")
                        for clause_type, payload in clauses.items():
                            status = payload.get("status", "unknown") if isinstance(payload, dict) else "unknown"
                            title = titleize_key(clause_type)
                            if clause_search and clause_search.lower() not in title.lower():
                                continue
                            if clause_filter == "Found" and status != "found":
                                continue
                            if clause_filter == "Needs Review" and status not in {"needs_review", "partial", "partially_found"}:
                                continue
                            if clause_filter == "Not Found" and status not in {"not_found", "missing"}:
                                continue
                            render_clause_card(clause_type, payload, clause_explanations.get(clause_type))

                        # Store validated found clauses only for evaluation
                        st.session_state.current_clauses = {k:v.get("extracted_text") for k,v in clauses.items() if isinstance(v, dict) and v.get("status")=="found" and v.get("extracted_text")}
                    elif response is not None:
                        st.error("Failed to analyze contract")
                        try:
                            error_data = response.json()
                            st.error(f"Error details: {error_data.get('detail', 'Unknown error')}")
                        except Exception:
                            pass

        with col2:
            if "current_clauses" in st.session_state:
                if st.button("Evaluate Contract Health"):
                    with st.spinner("Evaluating contract health..."):
                        clauses = st.session_state.current_clauses
                        eval_response = make_api_request(
                            "/genai/evaluate-contract",
                            "POST",
                            {"clauses": clauses, "response_language": response_language},
                        )

                        if eval_response and eval_response.status_code == 200:
                            evaluation = eval_response.json()
                            render_contract_evaluation(evaluation)
                        else:
                            st.error("Failed to evaluate contract")
            else:
                st.info("Please analyze the contract first to enable health evaluation")

        # Run full analysis pipeline
        if st.button("Run Complete Analysis Pipeline"):
            with st.spinner("Running complete analysis pipeline..."):
                # Trigger the backend analysis pipeline
                pipeline_response = make_api_request(
                    f"/contracts/{contract_id}/init-genai?response_language={response_language}",
                    "POST",
                )

                if pipeline_response and pipeline_response.status_code == 200:
                    st.success("Analysis pipeline completed successfully!")

                    # Display the analysis results
                    results = pipeline_response.json().get("results", {})
                    if results:
                        st.markdown("### Analysis Results")
                        health_result = results.get("health_evaluation", results)
                        render_contract_evaluation(health_result)

                        if results.get("clauses"):
                            st.markdown("#### Clause-by-Clause Summary")
                            for clause_name in results.get("clauses", {}).keys():
                                st.write(f"- {clause_name}")

                        report_pdf = build_pipeline_report_pdf(contract_title, results, st.session_state.get("selected_client_name"))
                        st.download_button(
                            "Download Final Report (PDF)",
                            data=report_pdf,
                            file_name=f"contract_report_{contract_id}.pdf",
                            mime="application/pdf",
                            key=f"download_report_{contract_id}",
                        )

                        # Store results in session state for later reference
                        st.session_state[f"analysis_results_{contract_id}"] = results
                else:
                    st.error("Failed to run analysis pipeline")
                    if pipeline_response:
                        try:
                            error_data = pipeline_response.json()
                            st.error(f"Error details: {error_data.get('detail', 'Unknown error')}")
                        except Exception:
                            pass

        st.markdown("---")
        st.subheader("Ask AI About This Contract")
        st.caption("AI-assisted review only — not legal advice. Answers stay grounded in this contract.")

        select_contract(contract_id)
        if "chat_messages_by_contract" not in st.session_state:
            st.session_state.chat_messages_by_contract = {}
        if "last_chat_error" not in st.session_state:
            st.session_state.last_chat_error = None

        messages_by_contract = st.session_state.chat_messages_by_contract
        if contract_id not in messages_by_contract:
            messages_by_contract[contract_id] = []
        chat_messages = messages_by_contract[contract_id]

        chat_mode_labels = {
            "Ask anything": "ask_anything",
            "Simple answer": "simple_answer",
            "Detailed analysis": "detailed_analysis",
            "Executive summary": "executive_summary",
            "Clause rewrite": "clause_rewrite",
            "Risk review": "risk_review",
        }
        selected_chat_mode = st.selectbox(
            "Response style",
            list(chat_mode_labels.keys()),
            key=f"chat_response_mode_{contract_id}",
            help="Choose how detailed or focused you want the assistant to be.",
        )

        chip_prompts = [
            "Hello",
            "What can you do?",
            "What clauses are missing?",
            "What are the main risks?",
            "Does this contract mention vacation?",
            "Rewrite the termination clause more clearly",
        ]
        st.markdown("**Try asking:**")
        chip_cols = st.columns(len(chip_prompts))
        selected_prompt = None
        for idx, prompt in enumerate(chip_prompts):
            with chip_cols[idx]:
                if st.button(prompt, key=f"chat_chip_{contract_id}_{idx}"):
                    selected_prompt = prompt

        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("Clear chat", key=f"clear_chat_{contract_id}"):
                st.session_state.chat_messages_by_contract[contract_id] = []
                st.session_state.last_chat_error = None
                st.rerun()

        render_chat_history(chat_messages)

        if chat_messages and chat_messages[-1].get("role") == "assistant":
            followups = chat_messages[-1].get("suggested_followups", [])[:3]
            if followups:
                st.markdown("**Suggested follow-ups:**")
                follow_cols = st.columns(len(followups))
                for idx, followup in enumerate(followups):
                    with follow_cols[idx]:
                        if st.button(followup, key=f"chat_followup_{contract_id}_{len(chat_messages)}_{idx}"):
                            selected_prompt = followup

        typed_prompt = st.chat_input(
            "Ask about clauses, risks, obligations, missing terms, or signing concerns...",
            key=f"current_chat_input_{contract_id}",
        )
        question = selected_prompt or typed_prompt

        if question and question.strip():
            question = question.strip()
            chat_messages.append({"role": "user", "content": question})
            st.session_state.last_chat_error = None

            with st.spinner("Reviewing the contract evidence..."):
                chat_response = make_api_request(
                    f"/contracts/{contract_id}/chat",
                    "POST",
                    {
                        "message": question,
                        "chat_history": chat_messages[-10:],
                        "response_language": response_language,
                        "response_mode": chat_mode_labels.get(selected_chat_mode, "ask_anything"),
                    },
                )

            if chat_response and chat_response.status_code == 200:
                payload = chat_response.json()
                chat_messages.append(
                    {
                        "role": "assistant",
                        "content": payload.get("answer", "I could not generate an answer."),
                        "answer_type": payload.get("answer_type"),
                        "confidence": payload.get("confidence"),
                        "evidence_snippets": payload.get("evidence_snippets", []),
                        "suggested_followups": payload.get("suggested_followups", []),
                        "limitations": payload.get("limitations"),
                    }
                )
            else:
                friendly_error = "I couldn’t reach the contract assistant service. Please make sure the backend is running."
                technical_detail = None
                if chat_response:
                    try:
                        error_data = chat_response.json()
                        technical_detail = error_data.get("detail")
                        if chat_response.status_code == 400:
                            friendly_error = "Please analyze this contract first so I have evidence to answer from."
                        elif chat_response.status_code == 503:
                            friendly_error = "The AI model is currently unavailable. Please check Ollama/OpenAI configuration and try again."
                        elif technical_detail:
                            friendly_error = "The contract assistant hit a problem, but no raw traceback is shown here."
                    except Exception:
                        technical_detail = chat_response.text[:800]
                st.session_state.last_chat_error = technical_detail
                chat_messages.append({"role": "assistant", "content": friendly_error, "answer_type": "error"})
            st.rerun()

        if st.session_state.last_chat_error:
            with st.expander("Technical details"):
                st.write(st.session_state.last_chat_error)

        # Add option to clear current contract and start over
        st.markdown("---")
        if st.button("Clear Contract and Start Over"):
            keys_to_remove = ["current_contract_id", "current_pdf_bytes", "current_contract_content", "current_contract_title", "current_clauses"]
            for key in keys_to_remove:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    elif "selected_client_id" in st.session_state:
        st.info("Upload a contract above to proceed with AI analysis")
    
    else:
        st.info("Please create a client and upload a contract to proceed with AI analysis")


def get_contracts_list():
    """Get list of all contracts for the current user"""
    response = make_api_request("/contracts")
    if response and response.status_code == 200:
        return response.json().get("contracts", [])
    return []


def clients_contracts_page():
    """Enhanced Clients and Contracts management page with full CRUD operations"""
    page_header("Clients and Contracts", "Manage clients, upload contracts, and launch analysis actions.", "Workspace")

    tab1, tab2 = st.tabs(["Client Management", "Contract Management"])

    with tab1:
        st.header("Client Management")
        
        # Create new client section
        st.subheader("Create New Client")
        with st.form("new_client_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Client Name*")
                new_email = st.text_input("Email*")
            with col2:
                new_phone = st.text_input("Phone (optional)")
            
            if st.form_submit_button("Create Client"):
                if new_name and new_email:
                    response = make_api_request(
                        "/clients",
                        "POST",
                        {
                            "name": new_name,
                            "email": new_email,
                            "phone": new_phone if new_phone else None,
                        },
                    )
                    if response and response.status_code == 200:
                        st.success(f"Client '{new_name}' created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create client")
                else:
                    st.error("Please fill in all required fields (*)")

        st.divider()
        
        # List and manage existing clients
        st.subheader("Existing Clients")
        clients = get_clients_list()
        
        if clients:
            st.write(f"Found {len(clients)} clients:")
            
            for client in clients:
                client_id = client.get('_id') or client.get('id')
                with st.expander(f"{client.get('name', 'Unknown')} ({client.get('email', 'No email')})"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**ID:** {client_id}")
                        st.write(f"**Name:** {client.get('name', 'N/A')}")
                        st.write(f"**Email:** {client.get('email', 'N/A')}")
                        st.write(f"**Phone:** {client.get('phone', 'N/A')}")
                        st.write(f"**Created:** {client.get('created_at', 'N/A')}")
                    
                    with col2:
                        # Edit client
                        if st.button("Edit", key=f"edit_{client_id}"):
                            st.session_state[f"editing_{client_id}"] = True
                        
                        # Delete client
                        if st.button("Delete", key=f"delete_{client_id}"):
                            response = make_api_request(f"/clients/{client_id}", "DELETE")
                            if response and response.status_code == 200:
                                st.success("Client deleted successfully!")
                                st.rerun()
                            else:
                                error_msg = "Failed to delete client"
                                if response:
                                    try:
                                        error_data = response.json()
                                        error_msg = error_data.get("detail", error_msg)
                                    except:
                                        pass
                                st.error(error_msg)
                    
                    # Edit form (shown when edit button is clicked)
                    if st.session_state.get(f"editing_{client_id}"):
                        st.markdown("---")
                        st.subheader("Edit Client")
                        with st.form(f"edit_form_{client_id}"):
                            edit_name = st.text_input("Name", value=client.get('name', ''))
                            edit_email = st.text_input("Email", value=client.get('email', ''))
                            edit_phone = st.text_input("Phone", value=client.get('phone', ''))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Save Changes"):
                                    if edit_name and edit_email:
                                        response = make_api_request(
                                            f"/clients/{client_id}",
                                            "PUT",
                                            {
                                                "name": edit_name,
                                                "email": edit_email,
                                                "phone": edit_phone if edit_phone else None,
                                            },
                                        )
                                        if response and response.status_code == 200:
                                            st.success("Client updated successfully!")
                                            del st.session_state[f"editing_{client_id}"]
                                            st.rerun()
                                        else:
                                            st.error("Failed to update client")
                                    else:
                                        st.error("Please fill in all required fields")
                            with col2:
                                if st.form_submit_button("Cancel"):
                                    del st.session_state[f"editing_{client_id}"]
                                    st.rerun()
        else:
            st.info("No clients found. Create your first client above.")

    with tab2:
        st.header("Contract Management")
        
        # Get all contracts
        contracts = get_contracts_list()
        
        if contracts:
            st.subheader("All Contracts")
            st.write(f"Found {len(contracts)} contracts:")
            
            for contract in contracts:
                contract_id = contract.get('_id') or contract.get('id')
                
                with st.expander(f"{contract.get('title', 'Untitled Contract')} - Client ID: {contract.get('client_id', 'N/A')}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Contract ID:** {contract_id}")
                        st.write(f"**Title:** {contract.get('title', 'N/A')}")
                        st.write(f"**Client ID:** {contract.get('client_id', 'N/A')}")
                        st.write(f"**Status:** {contract.get('status', 'N/A')}")
                        st.write(f"**Created:** {contract.get('created_at', 'N/A')}")
                        # if contract.get('content'):
                        #     with st.expander("View Content"):
                        #         st.text(contract['content'][:500] + "..." if len(contract['content']) > 500 else contract['content'])
                    
                    with col2:
                        # Edit contract
                        if st.button("Edit", key=f"edit_contract_{contract_id}"):
                            st.session_state[f"editing_contract_{contract_id}"] = True
                        
                        # Delete contract
                        if st.button("Delete", key=f"delete_contract_{contract_id}"):
                            response = make_api_request(f"/contracts/{contract_id}", "DELETE")
                            if response and response.status_code == 200:
                                st.success("Contract deleted successfully!")
                                st.rerun()
                            else:
                                error_msg = "Failed to delete contract"
                                if response:
                                    try:
                                        error_data = response.json()
                                        error_msg = error_data.get("detail", error_msg)
                                    except:
                                        pass
                                st.error(error_msg)
                        
                        # Analyze with AI (if not already analyzed)
                        if contract.get('status') != 'analyzed':
                            if st.button("Analyze", key=f"analyze_contract_{contract_id}"):
                                with st.spinner("Running AI analysis..."):
                                    response = make_api_request(
                                        f"/contracts/{contract_id}/init-genai?response_language={st.session_state.get('response_language_selector', 'english')}",
                                        "POST",
                                    )
                                    if response and response.status_code == 200:
                                        st.success("Analysis completed!")
                                        
                                        # Display the analysis results
                                        results = response.json().get("results", {})
                                        if results:
                                            st.markdown("#### Analysis Results")
                                            render_contract_evaluation(results.get("health_evaluation", results))
                                        
                                        st.rerun()
                                    else:
                                        st.error("Analysis failed")
                                        if response:
                                            try:
                                                error_data = response.json()
                                                st.error(f"Error details: {error_data.get('detail', 'Unknown error')}")
                                            except Exception:
                                                pass
                    
                    # Edit form (shown when edit button is clicked)
                    if st.session_state.get(f"editing_contract_{contract_id}"):
                        st.markdown("---")
                        st.subheader("Edit Contract")
                        
                        # Get available clients for dropdown
                        clients = get_clients_list()
                        client_options = {f"{c.get('name', 'Unknown')} ({c.get('_id') or c.get('id')})": c.get('_id') or c.get('id') for c in clients}
                        
                        with st.form(f"edit_contract_form_{contract_id}"):
                            edit_title = st.text_input("Title", value=contract.get('title', ''))
                            
                            # Client selection
                            current_client_id = contract.get('client_id')
                            current_client_display = None
                            for display, cid in client_options.items():
                                if cid == current_client_id:
                                    current_client_display = display
                                    break
                            
                            if current_client_display:
                                current_index = list(client_options.keys()).index(current_client_display)
                            else:
                                current_index = 0
                            
                            selected_client = st.selectbox(
                                "Client", 
                                options=list(client_options.keys()),
                                index=current_index
                            )
                            edit_client_id = client_options[selected_client]
                            
                            edit_content = st.text_area("Content", value=contract.get('content', ''), height=100)
                            edit_status = st.selectbox("Status", options=["pending", "analyzed"], index=0 if contract.get('status') == 'pending' else 1)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Save Changes"):
                                    if edit_title and edit_client_id:
                                        response = make_api_request(
                                            f"/contracts/{contract_id}",
                                            "PUT",
                                            {
                                                "title": edit_title,
                                                "client_id": edit_client_id,
                                                "content": edit_content,
                                                "status": edit_status,
                                            },
                                        )
                                        if response and response.status_code == 200:
                                            st.success("Contract updated successfully!")
                                            del st.session_state[f"editing_contract_{contract_id}"]
                                            st.rerun()
                                        else:
                                            st.error("Failed to update contract")
                                    else:
                                        st.error("Please fill in all required fields")
                            with col2:
                                if st.form_submit_button("Cancel"):
                                    del st.session_state[f"editing_contract_{contract_id}"]
                                    st.rerun()
        else:
            st.info("No contracts found. Create contracts using the 'Contract Analysis' workflow.")
            
        st.divider()
        st.markdown("**Note:** To create new contracts with AI analysis, use the 'Contract Analysis' tab.")




def render_benchmark_comparison(payload: Dict[str, Any]):
    context = payload.get("benchmark_context", {})
    overall = payload.get("overall_position", {})
    st.subheader(payload.get("benchmark_title", "Benchmark Comparison"))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Benchmark Alignment Score", f"{overall.get('alignment_score', 'N/A')}/100")
    with c2:
        st.metric("Position", overall.get("position_label", "N/A"))
    with c3:
        st.metric("Confidence", context.get("confidence_label", "N/A"))

    st.markdown("### Benchmark Context")
    st.info(
        f"**Contract type:** {context.get('contract_type', 'N/A')}\n\n"
        f"**Region / jurisdiction:** {context.get('region', 'N/A')} / {context.get('jurisdiction', 'Not clearly detected')}\n\n"
        f"**Benchmark basis:** {context.get('benchmark_basis', 'Rule-based benchmark standard')}\n\n"
        f"**Sample size:** {context.get('sample_size') or 'Not applicable'}"
    )
    for limitation in context.get("limitations", []):
        st.caption(f"Limitation: {limitation}")

    st.markdown("### Overall Position")
    st.success(overall.get("executive_summary", "No executive summary available."))
    reasons = overall.get("top_reasons_for_score", [])
    if reasons:
        st.markdown("**Top reasons for score**")
        for reason in reasons[:3]:
            st.write(f"- {reason}")

    st.markdown("### Your Contract vs Benchmark")
    rows = payload.get("your_contract_vs_benchmark", [])
    if rows:
        display_rows = [
            {
                "Review Area": r.get("review_area"),
                "Your Contract": r.get("your_contract"),
                "Benchmark Expectation": r.get("benchmark_expectation"),
                "Result": r.get("result"),
                "Severity": r.get("severity"),
                "Recommendation": r.get("recommendation"),
            }
            for r in rows
        ]
        st.dataframe(display_rows, use_container_width=True, hide_index=True)
        with st.expander("Evidence behind benchmark rows"):
            for r in rows:
                evidence = r.get("evidence", [])
                if evidence:
                    st.markdown(f"**{r.get('review_area')}**")
                    for ev in evidence:
                        st.info(ev.get("quote", ""))
                        if ev.get("location"):
                            st.caption(ev.get("location"))
    else:
        st.warning("No benchmark rows were generated.")

    st.markdown("### Market Terms Comparison")
    terms = payload.get("market_terms_comparison", [])
    if terms:
        st.dataframe([
            {
                "Term": t.get("term"),
                "Your Contract": t.get("your_contract"),
                "Benchmark Expectation / Average": t.get("benchmark_average"),
                "Benchmark Range": t.get("benchmark_range"),
                "Difference": t.get("difference"),
                "Interpretation": t.get("interpretation"),
                "Limitations": t.get("limitations"),
            }
            for t in terms
        ], use_container_width=True, hide_index=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Strengths")
        strengths = payload.get("strengths", [])
        if strengths:
            for item in strengths:
                st.write(f"✅ {item}")
        else:
            st.caption("No major benchmark strengths identified yet.")
    with col_b:
        st.markdown("### Gaps")
        gaps = payload.get("gaps", [])
        if gaps:
            for item in gaps[:8]:
                st.write(f"⚠️ {item}")
        else:
            st.caption("No major benchmark gaps identified.")

    st.markdown("### Priority Recommendations")
    priorities = payload.get("priority_recommendations", {})
    st.markdown("**Priority 1 — Must Fix Before Approval**")
    for item in priorities.get("priority_1_must_fix", []) or ["No critical benchmark fixes identified."]:
        st.write(f"- {item}")
    st.markdown("**Priority 2 — Recommended Enhancements**")
    for item in priorities.get("priority_2_recommended", []) or ["No recommended benchmark enhancements identified."]:
        st.write(f"- {item}")

    st.markdown("### AI Commentary")
    st.write(payload.get("ai_commentary", "AI commentary unavailable."))

    with st.expander("Debug: Raw Benchmark Response"):
        st.json(payload)

def benchmark_page():
    """Professional Benchmark Comparison page."""
    page_header("Benchmark", "Compare this contract against benchmark expectations for its contract type.", "Contract comparison")

    contracts = get_contracts_list()
    if not contracts:
        st.info("No contracts found. Upload and analyze a contract first.")
        return

    options = {f"{c.get('title', 'Untitled Contract')} ({c.get('_id') or c.get('id')})": c.get('_id') or c.get('id') for c in contracts}
    selected_label = st.selectbox("Select analyzed contract", list(options.keys()))
    selected_contract_id = options[selected_label]

    if st.button("Run Benchmark Comparison", type="primary"):
        with st.spinner("Building benchmark comparison from validated clauses..."):
            response = make_api_request(f"/benchmark/compare/{selected_contract_id}", "POST")
        if response and response.status_code == 200:
            st.session_state[f"benchmark_comparison_{selected_contract_id}"] = response.json()
            st.success("Benchmark comparison completed.")
        else:
            st.error("Benchmark comparison failed")
            if response:
                try:
                    st.error(response.json().get("detail", "Unknown error"))
                except Exception:
                    pass

    payload = st.session_state.get(f"benchmark_comparison_{selected_contract_id}")
    if payload:
        render_benchmark_comparison(payload)
    else:
        st.info("Run Benchmark Comparison to see context, score, contract-vs-benchmark rows, market terms, gaps, and recommendations.")


def admin_dashboard():
    """Admin dashboard with metrics and logs"""
    st.title("Admin Dashboard")

    tab1, tab2 = st.tabs(["Metrics", "Logs"])

    with tab1:
        st.header("System Metrics")

        # Get metrics
        response = make_api_request("/metrics")
        if response and response.status_code == 200:
            metrics = response.json()

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Requests", metrics["total_requests"])

            with col2:
                st.metric("Successful Requests", metrics["successful_requests"])

            with col3:
                st.metric("Failed Requests", metrics["failed_requests"])

            with col4:
                st.metric("Success Rate", f"{metrics['success_rate']:.1f}%")

            chat_quality_response = make_api_request("/metrics/chat-quality")
            if chat_quality_response and chat_quality_response.status_code == 200:
                cq = chat_quality_response.json()
                st.markdown("#### Chat Quality")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Low Confidence Rate", f"{cq.get('low_confidence_rate', 0):.1f}%")
                with c2:
                    st.metric("Out-of-Scope Rate", f"{cq.get('out_of_scope_rate', 0):.1f}%")
                with c3:
                    st.metric("No Evidence Rate", f"{cq.get('no_evidence_rate', 0):.1f}%")

        # Health checks
        st.subheader("Health Checks")
        col1, col2 = st.columns(2)

        with col1:
            health_response = make_api_request("/healthz", auth=False)
            if health_response and health_response.status_code == 200:
                st.success("Health Check: OK")
            else:
                st.error("Health Check: Failed")

        with col2:
            ready_response = make_api_request("/readyz", auth=False)
            if ready_response and ready_response.status_code == 200:
                st.success("Readiness Check: OK")
            else:
                st.error("Readiness Check: Failed")

    with tab2:
        st.header("System Logs")

        # Filters
        col1, col2, col3 = st.columns(3)

        with col1:
            user_filter = st.text_input("Filter by User")

        with col2:
            endpoint_filter = st.text_input("Filter by Endpoint")

        with col3:
            status_filter = st.selectbox("Filter by Status", ["", "success", "error"])

        # Get logs
        params = {}
        if user_filter:
            params["user"] = user_filter
        if endpoint_filter:
            params["endpoint"] = endpoint_filter
        if status_filter:
            params["status"] = status_filter

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        endpoint = f"/logs?{query_string}" if query_string else "/logs"

        response = make_api_request(endpoint)
        if response and response.status_code == 200:
            logs_data = response.json()
            logs = logs_data["logs"]

            if logs:
                df = pd.DataFrame(logs)
                st.dataframe(df, use_container_width=True)

                st.write(f"Total logs: {logs_data['total']}")
                st.write(f"Page: {logs_data['page']} of {logs_data['pages']}")
            else:
                st.info("No logs found")



def dashboard_page():
    render_brand_logo("Professional contract review workspace")
    page_header("Dashboard", "Your contract review command center. Start with a client, upload a contract, then run analysis.", "Overview")
    stats = get_dashboard_stats()
    contracts = get_contracts_list()
    analyzed_contracts = sum(1 for contract in contracts if contract.get("status") == "analyzed")
    benchmark_outliers = sum(1 for contract in contracts if (contract.get("benchmark_result") or {}).get("overall_position", {}).get("alignment_score", 100) < 50)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_metric_card("Total Contracts", str(stats.get("contracts", len(contracts) or 0)), "Uploaded contracts")
    with c2:
        render_metric_card("Clients", str(stats.get("clients", 0)), "Active workspaces")
    with c3:
        render_metric_card("Analyses Completed", str(analyzed_contracts), "Ready for review")
    with c4:
        render_metric_card("Average Contract Health", "N/A", "Run health review to calculate")
    with c5:
        render_metric_card("Benchmark Outliers", str(benchmark_outliers), "Need closer review")

    if not contracts:
        empty_state(
            "Start by adding a client and uploading your first contract.",
            "Once a contract is uploaded, you can run clause analysis, check contract health, compare benchmarks, and ask AI questions.",
            "Go to Clients or Analyze to begin.",
        )
    else:
        st.markdown("### Recent contracts")
        recent_rows = [
            {
                "Contract": contract.get("title", "Untitled contract"),
                "Status": titleize_key(contract.get("status", "uploaded")),
                "Created": str(contract.get("created_at", "N/A"))[:19],
            }
            for contract in contracts[:6]
        ]
        st.dataframe(recent_rows, use_container_width=True, hide_index=True)

    render_next_step("Recommended next step", "Select a client, upload a contract, then run Contract Analysis to unlock health review, benchmark comparison, and AI Assistant.")


def ask_ai_page():
    page_header("AI Assistant", "Ask contract-specific questions grounded in extracted evidence.", "Contract assistant")
    empty_state("Use Ask AI inside Contract Analysis", "Select or upload a contract, then use the chat panel attached to that contract so history and evidence stay scoped correctly.", "Go to Contract Analysis → Ask AI About This Contract")


def settings_diagnostics_page():
    page_header("Settings", "Check app, AI, and database readiness without exposing secrets.", "Diagnostics")
    health = make_api_request("/healthz", auth=False)
    if health and health.status_code == 200:
        st.markdown("### API Health")
        st.success("Backend API is responding.")
        with st.expander("Debug: API health response"):
            st.json(health.json())
    llm = make_api_request("/llm/health", auth=False)
    if llm and llm.status_code == 200:
        llm_payload = llm.json()
        status = "Online" if llm_payload.get("reachable") else "Offline"
        st.markdown("### LLM Health")
        st.info(f"AI provider: {llm_payload.get('ai_provider', 'Unknown')} · Status: {status}")
        with st.expander("Debug: LLM health response"):
            st.json(llm_payload)

def main():
    """Main application"""
    st.set_page_config(
        page_title="Contract Intelligence", page_icon="⚖️", layout="wide"
    )

    if "sidebar_compact" not in st.session_state:
        st.session_state.sidebar_compact = False

    apply_modern_theme(st.session_state.sidebar_compact)
    apply_global_css(st.session_state.sidebar_compact)

    # Check if user is logged in
    if not st.session_state.token:
        login_page()
        return
    

    # Sidebar navigation
    with st.sidebar:
        render_brand_logo("Contract review workspace")
        st.caption(f"Signed in as {st.session_state.username}")
        st.toggle("Compact sidebar", key="sidebar_compact")
        st.markdown("---")
        nav_items = [
            "Dashboard",
            "Clients",
            "Contracts",
            "Analyze",
            "Benchmark",
            "AI Assistant",
            "Settings",
        ]
        if not BENCHMARK_ENABLED:
            nav_items.remove("Benchmark")
        navigation = st.radio("Navigate", nav_items, label_visibility="collapsed")
        st.markdown("---")
        if st.button("Log out"):
            clear_session()
            st.rerun()

    render_chrome_header(st.session_state.username)

    st.markdown("<div class='page-transition'>", unsafe_allow_html=True)

    # Main content
    if navigation == "Dashboard":
        dashboard_page()
    elif navigation in {"Clients", "Contracts"}:
        clients_contracts_page()
        st.markdown("<div class='fab-chip'>➕ Main Action: Create Client / Contract</div>", unsafe_allow_html=True)
    elif navigation == "Analyze":
        contract_analysis_page()
        st.markdown("<div class='fab-chip'>✨ Main Action: Analyze Contract</div>", unsafe_allow_html=True)
    elif navigation == "Benchmark":
        benchmark_page()
        st.markdown("<div class='fab-chip'>📚 Main Action: Run Benchmark</div>", unsafe_allow_html=True)
    elif navigation == "AI Assistant":
        ask_ai_page()
    elif navigation == "Settings":
        settings_diagnostics_page()
        st.markdown("---")
        admin_dashboard()

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
