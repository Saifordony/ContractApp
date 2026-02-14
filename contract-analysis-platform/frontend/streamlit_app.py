import streamlit as st
import requests
import os
from typing import Dict
import pandas as pd
import fitz  # PyMuPDF

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Initialize session state
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None


def apply_modern_theme():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(120deg, #eef3f6 0%, #e7eef2 100%);
        }
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            color: #20263a;
            letter-spacing: -0.02em;
            font-weight: 700;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1f2338 0%, #232845 100%);
            border-right: 1px solid #2f365c;
        }
        section[data-testid="stSidebar"] * {
            color: #eef1ff !important;
        }
        div[data-testid="stTabs"] button {
            border-radius: 10px 10px 0 0;
            background: transparent;
            color: #2b3248;
            font-weight: 700;
            border: none;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: #21263b !important;
            color: #ffffff !important;
        }
        div[data-testid="stForm"], div[data-testid="stExpander"] {
            background: #f8fbfc;
            border: 1px solid #d6dfe5;
            border-radius: 14px;
            padding: 0.5rem;
        }
        .stButton > button {
            border-radius: 10px;
            border: 1px solid #2e344f;
            background: linear-gradient(90deg, #21263b 0%, #343b5a 100%);
            color: white;
            font-weight: 700;
            box-shadow: 0 4px 12px rgba(24, 28, 43, 0.25);
        }
        .stButton > button:hover {
            opacity: 0.95;
            transform: translateY(-2px);
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d9e2e8;
            border-radius: 12px;
            padding: 10px;
            box-shadow: 0 2px 8px rgba(18, 24, 38, 0.08);
        }
        .dashboard-chip {
            background: #20263a;
            color: #ffffff;
            border-radius: 12px;
            padding: 0.65rem 0.9rem;
            border: 1px solid #313954;
            margin-bottom: 0.45rem;
        }
        .topbar {
            background: #f4f7f8;
            border: 1px solid #d9e2e8;
            border-radius: 14px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .topbar-title {
            font-weight: 800;
            color: #1f2438;
            letter-spacing: 0.02em;
        }
        .topbar-sub {
            color: #5c647c;
            font-size: 0.9rem;
        }
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
        st.markdown(
            f"<div class='dashboard-chip'><b>Total Requests</b><br>{stats['total_requests']}</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='dashboard-chip'><b>Success Rate</b><br>{stats['success_rate']}</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"<div class='dashboard-chip'><b>Clients</b><br>{stats['clients']}</div>",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"<div class='dashboard-chip'><b>Contracts</b><br>{stats['contracts']}</div>",
            unsafe_allow_html=True,
        )


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


def login_page():
    """Login and Registration page"""
    st.title("Contract Analysis Platform")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.header("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

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
        st.header("Register")
        with st.form("register_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Register")

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
                        st.success("Registration successful! Please login.")
                    else:
                        st.error(
                            "Registration failed. Username or email might already exist."
                        )


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
                    with st.expander(f"Contract: {contract.get('title', 'Untitled')}"):
                        st.write(f"**ID:** {contract.get('_id', 'N/A')}")
                        st.write(f"**Status:** {contract.get('status', 'N/A')}")
                        st.write(f"**Created:** {contract.get('created_at', 'N/A')}")

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

    if (
        "current_contract_id" in st.session_state
        and "current_pdf_bytes" in st.session_state
    ):
        st.header("AI Contract Analysis")

        contract_id = st.session_state.current_contract_id
        pdf_bytes = st.session_state.current_pdf_bytes
        contract_title = st.session_state.get("current_contract_title", "Unknown")
        
        # Show contract being analyzed
        st.info(f"Analyzing contract: **{contract_title}** (ID: {contract_id})")

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
                    # Create a temporary file-like object for the API
                    files = {"file": ("contract.pdf", pdf_bytes, "application/pdf")}
                    response = make_api_request(
                        "/genai/analyze-contract",
                        "POST",
                        data={"response_language": response_language, "use_ocr": use_ocr},
                        files=files,
                    )

                    if response and response.status_code == 200:
                        data = response.json()
                        clauses = data["clauses"]

                        st.success("Contract analyzed successfully!")
                        st.subheader("Extracted Clauses")

                        for clause_type, content in clauses.items():
                            with st.expander(f"{clause_type}"):
                                st.write(content)

                        # Store clauses for evaluation
                        st.session_state.current_clauses = clauses
                    else:
                        st.error("Failed to analyze contract")
                        if response:
                            try:
                                error_data = response.json()
                                st.error(f"Error details: {error_data.get('detail', 'Unknown error')}")
                            except:
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

                            if evaluation["approved"]:
                                st.success("Contract Approved")
                            else:
                                st.error("Contract Not Approved")

                            st.write("**Reasoning:**")
                            st.write(evaluation["reasoning"])
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
                        
                        # Display approval status
                        approved = results.get("approved", False)
                        if approved:
                            st.success("Contract Approved")
                        else:
                            st.error("Contract Not Approved")
                        
                        # Display reasoning
                        reasoning = results.get("reasoning", "No reasoning provided")
                        st.markdown("#### Reasoning")
                        st.write(reasoning)
                        
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

        for msg in st.session_state[chat_key]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_question = st.chat_input("Ask a question about this contract...")
        if user_question:
            st.session_state[chat_key].append({"role": "user", "content": user_question})
            with st.chat_message("user"):
                st.write(user_question)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    chat_response = make_api_request(
                        f"/contracts/{contract_id}/chat",
                        "POST",
                        {"question": user_question, "response_language": response_language},
                    )

                    if chat_response and chat_response.status_code == 200:
                        answer = chat_response.json().get("answer", "No answer returned")
                        st.write(answer)
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
        
        # Add option to clear current contract and start over
        st.markdown("---")
        if st.button("Clear Contract and Start Over"):
            keys_to_remove = ["current_contract_id", "current_pdf_bytes", "current_contract_title", "current_clauses"]
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
                                            
                                            # Display approval status
                                            approved = results.get("approved", False)
                                            if approved:
                                                st.success("Contract Approved")
                                            else:
                                                st.error("Contract Not Approved")
                                            
                                            # Display reasoning
                                            reasoning = results.get("reasoning", "No reasoning provided")
                                            st.markdown("**Reasoning:**")
                                            st.write(reasoning)
                                        
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
    apply_modern_theme()

    # Check if user is logged in
    if not st.session_state.token:
        login_page()
        return
    

    # Sidebar navigation (functional)
    st.sidebar.title(f"Welcome, {st.session_state.username}")
    st.sidebar.caption("Arabic + English OCR and bilingual AI responses enabled")
    st.sidebar.markdown("---")
    navigation = st.sidebar.radio(
        "Navigate",
        ["🏠 Contract Analysis", "🗂️ Data Management", "📊 Admin Dashboard"],
        label_visibility="collapsed",
    )

    if st.sidebar.button("Logout"):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    render_chrome_header(st.session_state.username)

    # Main content
    if navigation == "🏠 Contract Analysis":
        contract_analysis_page()

    elif navigation == "🗂️ Data Management":
        clients_contracts_page()

    elif navigation == "📊 Admin Dashboard":
        admin_dashboard()


if __name__ == "__main__":
    main()
