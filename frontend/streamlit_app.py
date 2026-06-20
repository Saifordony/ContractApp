import os
from typing import Any
import requests
import streamlit as st
from frontend.styles.global_css import APP_CSS

st.set_page_config(page_title="Contract Intelligence", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
FRONTEND_BUILD = "streamlit-clean-rebuild-v1"


def init_state():
    defaults = {"token": None, "user": None, "page": "Home", "auth_mode": "login", "selected_contract_id": None}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def api_request(method: str, path: str, **kwargs) -> tuple[bool, Any]:
    headers = kwargs.pop("headers", {})
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        response = requests.request(method, f"{API_BASE_URL}{path}", headers=headers, timeout=30, **kwargs)
        if response.status_code == 401:
            st.session_state.token = None
            st.session_state.user = None
            return False, "Your session expired. Please sign in again."
        if response.status_code >= 400:
            try: detail = response.json().get("detail", "Request failed.")
            except Exception: detail = "Request failed. Please try again."
            return False, detail
        return True, response.json()
    except requests.RequestException:
        return False, "Backend is not reachable. Confirm FastAPI is running on port 8000."


def health_marker():
    try:
        r = requests.get(f"{API_BASE_URL}/healthz", timeout=3)
        return r.json() if r.ok else {"Backend Build": "unreachable"}
    except requests.RequestException:
        return {"Backend Build": "unreachable"}


def user_message(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        detail = value.get("detail") or value.get("message") or value.get("error")
        if isinstance(detail, str):
            return detail
        if detail is not None:
            return str(detail)
        return "; ".join(f"{key}: {val}" for key, val in value.items()) or "Something went wrong."
    if isinstance(value, list):
        return "; ".join(user_message(item) for item in value) or "Something went wrong."
    return str(value) if value is not None else "Something went wrong."


def render_sidebar():
    health = health_marker()
    st.sidebar.markdown("### Contract Intelligence")
    st.sidebar.caption("Active Frontend: Streamlit")
    st.sidebar.caption("Active Frontend File: frontend/streamlit_app.py")
    st.sidebar.caption(f"Frontend Build: {FRONTEND_BUILD}")
    st.sidebar.caption(f"Backend Build: {health.get('Backend Build', 'unknown')}")
    if st.session_state.user:
        st.sidebar.divider()
        st.sidebar.caption("Signed in as")
        st.sidebar.write(st.session_state.user.get("email"))
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()
        st.sidebar.divider()
        pages = ["Home", "Clients", "Contracts", "Contract Analysis", "Contract Chat", "Benchmark", "Settings / System Health"]
        st.session_state.page = st.sidebar.radio("Navigate", pages, index=pages.index(st.session_state.page) if st.session_state.page in pages else 0)


def auth_screen():
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown('<div class="cip-hero"><span class="cip-pill">Contract Intelligence</span><h1>Review contracts with evidence, risk, and clarity.</h1><p class="cip-muted">Secure Streamlit MVP backed by FastAPI, MongoDB, and grounded rule-based analysis.</p></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.05, 1])
    with col2:
        st.write("")
        mode = st.radio("Account action", ["Sign In", "Create Account"], horizontal=True, label_visibility="collapsed")
        st.session_state.auth_mode = "register" if mode == "Create Account" else "login"
        st.markdown('<div class="cip-auth-card">', unsafe_allow_html=True)
        with st.container():
            if st.session_state.auth_mode == "register":
                st.header("Create account")
                with st.form("register_form"):
                    full_name = st.text_input("Full name", autocomplete="name")
                    email = st.text_input("Email", autocomplete="email")
                    password = st.text_input("Password", type="password", autocomplete="new-password")
                    confirm = st.text_input("Confirm password", type="password", autocomplete="new-password")
                    submitted = st.form_submit_button("Create account", use_container_width=True)
                if submitted:
                    if len(full_name.strip()) < 2:
                        st.error("Enter your full name.")
                    elif "@" not in email:
                        st.error("Enter a valid email address.")
                    elif len(password) < 8:
                        st.error("Password must be at least 8 characters.")
                    elif password != confirm:
                        st.error("Passwords do not match.")
                    else:
                        with st.spinner("Creating account..."):
                            ok, data = api_request("POST", "/auth/register", json={"full_name": full_name, "email": email, "password": password})
                        if ok:
                            st.success("Account created. Please sign in.")
                            st.session_state.auth_mode = "login"
                        else:
                            st.error(user_message(data))
            else:
                st.header("Log in")
                with st.form("login_form"):
                    email = st.text_input("Email", autocomplete="email")
                    password = st.text_input("Password", type="password", autocomplete="current-password")
                    submitted = st.form_submit_button("Log in", use_container_width=True)
                if submitted:
                    if not email or not password:
                        st.error("Email and password are required.")
                    else:
                        with st.spinner("Signing in..."):
                            ok, data = api_request("POST", "/auth/login", json={"email": email, "password": password})
                        if ok:
                            st.session_state.token = data["access_token"]
                            st.session_state.user = data["user"]
                            st.rerun()
                        else:
                            st.error(user_message(data))
        st.markdown('</div>', unsafe_allow_html=True)


def require_auth():
    if not st.session_state.token:
        return False
    ok, data = api_request("GET", "/auth/me")
    if ok:
        st.session_state.user = data
        return True
    st.warning(user_message(data))
    return False


def home():
    st.title("Home Dashboard")
    ok_c, clients = api_request("GET", "/clients")
    ok_k, contracts = api_request("GET", "/contracts")
    c1,c2,c3 = st.columns(3)
    c1.metric("Clients", len(clients) if ok_c else 0)
    c2.metric("Contracts", len(contracts) if ok_k else 0)
    c3.metric("Review status", "Ready")
    st.info("Start by creating a client, uploading a contract, then running analysis, chat, and benchmark workflows.")


def clients_page():
    st.title("Clients")
    with st.form("client_form", clear_on_submit=True):
        name = st.text_input("Client name")
        industry = st.text_input("Industry")
        notes = st.text_area("Notes")
        if st.form_submit_button("Create client"):
            ok, data = api_request("POST", "/clients", json={"name": name, "industry": industry, "notes": notes})
            if ok:
                st.success("Client created.")
            else:
                st.error(user_message(data))
    ok, data = api_request("GET", "/clients")
    if ok and data:
        st.dataframe(data, use_container_width=True)
    else:
        st.caption("No clients yet.")


def contracts_page():
    st.title("Contracts")
    ok, clients = api_request("GET", "/clients")
    client_options = {c["name"]: c["id"] for c in clients} if ok else {}
    with st.form("upload_form"):
        name = st.text_input("Contract name")
        client_name = st.selectbox("Client", ["No client"] + list(client_options.keys()))
        file = st.file_uploader("Upload PDF, DOCX, or TXT", type=["pdf", "docx", "txt"])
        if st.form_submit_button("Upload contract"):
            if not file:
                st.error("Choose a contract file.")
            else:
                files = {"file": (file.name, file.getvalue())}
                data = {"name": name or file.name}
                if client_name != "No client":
                    data["client_id"] = client_options[client_name]
                ok, resp = api_request("POST", "/contracts/upload", files=files, data=data)
                if ok:
                    st.success("Contract uploaded.")
                else:
                    st.error(user_message(resp))
    ok, contracts = api_request("GET", "/contracts")
    if ok and contracts:
        st.dataframe([{k:v for k,v in c.items() if k != "extracted_text"} for c in contracts], use_container_width=True)
    else:
        st.caption("No contracts uploaded yet.")


def select_contract():
    ok, contracts = api_request("GET", "/contracts")
    if not ok or not contracts:
        st.warning("Upload a contract first.")
        return None
    labels = {f"{c['name']} ({c['id'][:6]})": c["id"] for c in contracts}
    chosen = st.selectbox("Contract", list(labels.keys()))
    return labels[chosen]


def analysis_page():
    st.title("Contract Analysis")
    cid = select_contract()
    if cid and st.button("Run analysis", use_container_width=True):
        with st.spinner("Analyzing contract..."):
            ok, data = api_request("POST", f"/contracts/{cid}/analyze")
        if ok:
            st.metric("Health score", data["health_score"])
            st.write(data["executive_summary"])
            st.subheader("Risks")
            st.write(data["risks"])
            st.subheader("Clauses")
            st.write(data["clauses"])
        else:
            st.error(user_message(data))


def chat_page():
    st.title("Contract Chat")
    cid = select_contract()
    q = st.text_input("Ask a question grounded in this contract")
    if cid and st.button("Ask"):
        ok, data = api_request("POST", f"/contracts/{cid}/chat", json={"question": q})
        if ok:
            st.write(data["answer"])
            st.caption(f"Confidence: {data['confidence']}")
            st.write(data["evidence"])
        else:
            st.error(user_message(data))


def benchmark_page():
    st.title("Benchmark")
    cid = select_contract()
    if cid and st.button("Run benchmark", use_container_width=True):
        ok, data = api_request("POST", f"/contracts/{cid}/benchmark")
        if ok:
            st.metric("Overall score", data["overall_score"])
            st.write(data)
        else:
            st.error(user_message(data))


def settings_page():
    st.title("Settings / System Health")
    st.json(health_marker())
    st.caption(f"API Base URL: {API_BASE_URL}")


def main():
    init_state()
    render_sidebar()
    if not require_auth():
        auth_screen()
        return
    st.markdown(APP_CSS, unsafe_allow_html=True)
    {"Home": home, "Clients": clients_page, "Contracts": contracts_page, "Contract Analysis": analysis_page, "Contract Chat": chat_page, "Benchmark": benchmark_page, "Settings / System Health": settings_page}[st.session_state.page]()

if __name__ == "__main__":
    main()
