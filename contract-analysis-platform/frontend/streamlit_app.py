import streamlit as st
import requests
import os
import html
from typing import Dict
import pandas as pd
import fitz  # PyMuPDF

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
BENCHMARK_ENABLED = os.getenv("BENCHMARK_ENABLED", "true").lower() == "true"

# Initialize session state
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None


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
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>{title}</div>
            <div class='metric-value'>{value}</div>
            <div class='metric-sub'>{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chrome_header(username: str):
    stats = get_dashboard_stats()
    st.markdown(
        f"""
        <div class='topbar'>
            <div>
                <div class='topbar-title'>📊 CONTRACT INTELLIGENCE DASHBOARD</div>
                <div class='topbar-sub'>Welcome, {username} — bilingual OCR + AI analysis workspace</div>
            </div>
            <div class='topbar-sub'>EN | AR • Secure Session</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Total Requests", str(stats['total_requests']), "All tracked API calls")
    with c2:
        render_metric_card("Success Rate", str(stats['success_rate']), "Healthy backend responses")
    with c3:
        render_metric_card("Clients", str(stats['clients']), "Managed organizations")
    with c4:
        render_metric_card("Contracts", str(stats['contracts']), "Contracts in your workspace")


def make_api_request(
    endpoint: str,
    method: str = "GET",
    data: Dict = None,
    files: Dict = None,
    auth: bool = True,
):
    """Make API request with error handling"""
    headers = {}
    if auth and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        if method == "GET":
            response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers)
        elif method == "POST":
            if files:
                response = requests.post(
                    f"{API_BASE_URL}{endpoint}", headers=headers, files=files, data=data
                )
            else:
                headers["Content-Type"] = "application/json"
                response = requests.post(
                    f"{API_BASE_URL}{endpoint}", headers=headers, json=data
                )
        elif method == "PUT":
            headers["Content-Type"] = "application/json"
            response = requests.put(
                f"{API_BASE_URL}{endpoint}", headers=headers, json=data
            )
        elif method == "DELETE":
            response = requests.delete(f"{API_BASE_URL}{endpoint}", headers=headers)

        if response.status_code == 401:
            st.session_state.token = None
            st.session_state.username = None
            st.error("Session expired. Please login again.")
            st.rerun()

        return response
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None


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
    approved = evaluation.get("approved", False)
    if approved:
        st.success("Contract Approved")
    else:
        st.error("Contract Not Approved")

    risk_level = str(evaluation.get("risk_level", "medium")).lower()
    st.write(f"**Risk Level:** {risk_level.title()}")

    st.write("**Reasoning:**")
    st.write(evaluation.get("reasoning", "No reasoning provided"))

    missing = evaluation.get("missing_critical_clauses", [])
    issues = evaluation.get("issues", [])
    changes = evaluation.get("required_changes", [])

    if missing:
        st.markdown("#### Missing Critical Clauses")
        for item in missing:
            st.write(f"- {item}")

    if issues:
        st.markdown("#### Specific Issues Found")
        for item in issues:
            st.write(f"- {item}")

    if changes:
        st.markdown("#### What This Contract Needs")
        for item in changes:
            st.write(f"- {item}")


def render_chat_history(chat_messages):
    if not chat_messages:
        return

    st.markdown("<div class='chat-shell'><div class='chat-scroll'>", unsafe_allow_html=True)
    for msg in chat_messages:
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
    st.markdown("</div></div>", unsafe_allow_html=True)


def login_page():
    """Login and Registration page"""
    st.markdown("<div class='login-wrap'><div class='login-card'>", unsafe_allow_html=True)
    st.title("Contract Analysis Platform")
    st.caption("Use Sign In or Sign Up below.")

    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")

            if submit:
                response = make_api_request(
                    "/auth/login",
                    "POST",
                    {"username": username, "password": password},
                    auth=False,
                )

                if response and response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data["access_token"]
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Login failed. Please check your credentials.")

    with tab2:
        with st.form("register_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Sign Up")

            if submit:
                if password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    response = make_api_request(
                        "/auth/register",
                        "POST",
                        {"username": username, "email": email, "password": password},
                        auth=False,
                    )

                    if response and response.status_code == 200:
                        st.success("Registration successful! Please sign in.")
                    else:
                        st.error(
                            "Registration failed. Username or email might already exist."
                        )

    st.markdown("</div></div>", unsafe_allow_html=True)


def get_clients_list():
    """Get list of all clients for the current user"""
    response = make_api_request("/clients")
    if response and response.status_code == 200:
        return response.json().get("clients", [])
    return []


def contract_analysis_page():
    """Contract Analysis page"""
    st.title("Contract Analysis")
    
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
                        clauses = data["clauses"]
                        clause_explanations = data.get("clause_explanations", {})

                        st.success("Contract analyzed successfully!")
                        st.subheader("Extracted Clauses")

                        for clause_type, content in clauses.items():
                            with st.expander(f"{clause_type}"):
                                st.write(content)
                                explanation = clause_explanations.get(clause_type)
                                if explanation:
                                    st.markdown("**In simple terms:**")
                                    st.write(explanation)

                        # Store clauses for evaluation
                        st.session_state.current_clauses = clauses
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
                        render_contract_evaluation(results)
                        
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
        chat_key = f"contract_chat_history_{contract_id}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []

        render_chat_history(st.session_state[chat_key])

        with st.form(f"contract_chat_form_{contract_id}", clear_on_submit=True):
            q_col, send_col = st.columns([8, 1])
            with q_col:
                user_question = st.text_input(
                    "Ask a question about this contract...",
                    placeholder="Ask a question about this contract...",
                    label_visibility="collapsed",
                    key=f"chat_input_{contract_id}",
                )
            with send_col:
                send_clicked = st.form_submit_button("Send")

        if send_clicked:
            if not user_question or not user_question.strip():
                st.warning("Please enter a question first.")
            else:
                question = user_question.strip()
                st.session_state[chat_key].append({"role": "user", "content": question})

                with st.spinner("Thinking..."):
                    chat_response = make_api_request(
                        f"/contracts/{contract_id}/chat",
                        "POST",
                        {"question": question, "response_language": response_language},
                    )

                    if chat_response and chat_response.status_code == 200:
                        answer = chat_response.json().get("answer", "No answer returned")
                        st.session_state[chat_key].append(
                            {"role": "assistant", "content": answer}
                        )
                    else:
                        error_msg = "Failed to get AI answer"
                        if chat_response:
                            try:
                                error_data = chat_response.json()
                                error_msg = error_data.get("detail", error_msg)
                            except Exception:
                                pass
                        st.error(error_msg)
                st.rerun()
        
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
    st.title("Data Management")

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
                                            render_contract_evaluation(results)
                                        
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



def benchmark_page():
    """Benchmark Comparison page (additive feature)."""
    st.title("Benchmark Comparison")
    st.caption("Clause-level benchmarking only. Not legal advice.")

    with st.form("benchmark_form"):
        uploaded_file = st.file_uploader("Upload contract (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
        col1, col2, col3 = st.columns(3)
        with col1:
            contract_type = st.selectbox(
                "Contract Type",
                ["employment", "msa", "vendor", "nda", "other"],
            )
        with col2:
            jurisdiction = st.selectbox(
                "Jurisdiction",
                ["jordan", "usa", "uk", "eu", "other"],
            )
        with col3:
            industry = st.text_input("Industry (optional)")

        opt_in = st.checkbox("Opt-in: store embedding + minimal metadata for future benchmarks", value=False)
        submitted = st.form_submit_button("Run Benchmark")

    if submitted:
        if not uploaded_file:
            st.error("Please upload a contract file.")
            return

        with st.spinner("Running clause-level benchmark analysis..."):
            files = {"file": (uploaded_file.name, uploaded_file.read(), "application/octet-stream")}
            data = {
                "contract_type": contract_type,
                "jurisdiction": jurisdiction,
                "industry": industry,
                "opt_in_store_user_data": opt_in,
            }
            response = make_api_request("/benchmark/analyze", "POST", data=data, files=files)

        if response and response.status_code == 200:
            payload = response.json()
            clause_results = payload.get("clause_results", [])
            st.metric("Overall Alignment Score", payload.get("overall_score", "N/A"))
            st.caption(f"Compared {len(clause_results)} clause(s) from this contract.")

            fallbacks = payload.get("meta", {}).get("fallbacks_used", [])
            if fallbacks:
                st.info(f"Fallbacks used: {', '.join(fallbacks)}")

            if not clause_results:
                st.warning("No clauses detected from this file.")

            for clause in clause_results:
                label = clause.get("alignment_label", "yellow")
                badge = "🟢" if label == "green" else "🟡" if label == "yellow" else "🔴"
                score = clause.get("clause_score", "N/A")
                conf = clause.get("confidence", 0)
                with st.expander(f"{badge} {clause.get('clause_type', 'unknown')} — {score}/100"):
                    st.write(f"Confidence: {conf}")
                    st.write(f"Peers (N): {clause.get('benchmark_stats', {}).get('N', 0)}")

                    patterns = clause.get('typical_patterns', [])
                    if patterns:
                        st.write("Typical patterns:")
                        for pattern in patterns[:2]:
                            st.write(f"- {pattern}")

                    if clause.get("suggested_revision"):
                        st.write(f"Suggested revision: {clause['suggested_revision']}")

                    citations = clause.get("citations", [])
                    if citations:
                        st.write("References:")
                        for cit in citations[:2]:
                            st.write(f"- {cit.get('benchmark_clause_id')}: {cit.get('snippet_used')}")
        else:
            st.error("Benchmark analysis failed")
            if response:
                try:
                    st.error(response.json().get("detail", "Unknown error"))
                except Exception:
                    pass


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


def main():
    """Main application"""
    st.set_page_config(
        page_title="Contract Analysis Platform", page_icon="📄", layout="wide"
    )

    if "sidebar_compact" not in st.session_state:
        st.session_state.sidebar_compact = False

    apply_modern_theme(st.session_state.sidebar_compact)

    # Check if user is logged in
    if not st.session_state.token:
        login_page()
        return
    

    # Sidebar navigation (functional)
    st.sidebar.title("⚡ CAP")
    st.sidebar.caption(f"Welcome, {st.session_state.username}")
    st.sidebar.caption("Arabic + English OCR and bilingual AI responses enabled")
    st.sidebar.toggle("Compact sidebar", key="sidebar_compact")
    st.sidebar.markdown("---")
    navigation = st.sidebar.radio(
        "Navigate",
        (["🏠 Contract Analysis", "🗂️ Data Management", "📊 Admin Dashboard", "📚 Benchmark"] if BENCHMARK_ENABLED else ["🏠 Contract Analysis", "🗂️ Data Management", "📊 Admin Dashboard"]),
        label_visibility="collapsed",
    )

    if st.sidebar.button("Logout"):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    render_chrome_header(st.session_state.username)

    st.markdown("<div class='page-transition'>", unsafe_allow_html=True)

    # Main content
    if navigation == "🏠 Contract Analysis":
        contract_analysis_page()
        st.markdown("<div class='fab-chip'>✨ Main Action: Analyze Contract</div>", unsafe_allow_html=True)

    elif navigation == "🗂️ Data Management":
        clients_contracts_page()
        st.markdown("<div class='fab-chip'>➕ Main Action: Create Client / Contract</div>", unsafe_allow_html=True)

    elif navigation == "📊 Admin Dashboard":
        admin_dashboard()
        st.markdown("<div class='fab-chip'>📈 Main Action: Monitor Metrics</div>", unsafe_allow_html=True)

    elif navigation == "📚 Benchmark":
        benchmark_page()
        st.markdown("<div class='fab-chip'>📚 Main Action: Run Benchmark</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
