import json
import os
from typing import Any, Dict, Optional

import requests
import streamlit as st

st.set_page_config(page_title="ContractApp", layout="wide")

INTERNAL_API_BASE_URL = os.getenv("INTERNAL_API_BASE_URL", os.getenv("API_BASE_URL", "http://backend:8000")).rstrip("/")
PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", "http://localhost:8000").rstrip("/")


def _headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    token = st.session_state.get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _post(path: str, payload: Dict[str, Any]) -> requests.Response:
    return requests.post(
        f"{INTERNAL_API_BASE_URL}{path}",
        json=payload,
        headers=_headers(),
        timeout=60,
    )


def _get(path: str) -> requests.Response:
    return requests.get(
        f"{INTERNAL_API_BASE_URL}{path}",
        headers=_headers(),
        timeout=30,
    )


def _render_response(resp: requests.Response) -> None:
    st.write(f"Status: {resp.status_code}")
    try:
        st.json(resp.json())
    except Exception:
        st.code(resp.text)


st.title("ContractApp")
st.caption(f"Frontend URL: http://localhost:8501 | Public Backend URL: {PUBLIC_API_BASE_URL}")

with st.expander("Connection status", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        st.write("Internal API base (used by frontend server):")
        st.code(INTERNAL_API_BASE_URL)
    with col2:
        st.write("Public API base (for your browser/curl):")
        st.code(PUBLIC_API_BASE_URL)

    if st.button("Check backend health"):
        try:
            resp = _get("/healthz")
            _render_response(resp)
        except Exception as exc:
            st.error(f"Cannot reach backend: {exc}")

st.markdown("---")

# Auth section
st.subheader("1) Authentication")
col_reg, col_login = st.columns(2)

with col_reg:
    st.markdown("**Register**")
    reg_username = st.text_input("Username", key="reg_username")
    reg_email = st.text_input("Email", key="reg_email")
    reg_password = st.text_input("Password", type="password", key="reg_password")
    if st.button("Register user"):
        try:
            resp = _post(
                "/auth/register",
                {
                    "username": reg_username,
                    "email": reg_email,
                    "password": reg_password,
                },
            )
            _render_response(resp)
        except Exception as exc:
            st.error(f"Register failed: {exc}")

with col_login:
    st.markdown("**Login**")
    login_username = st.text_input("Login username", key="login_username")
    login_password = st.text_input("Login password", type="password", key="login_password")
    if st.button("Login"):
        try:
            resp = _post(
                "/auth/login",
                {"username": login_username, "password": login_password},
            )
            _render_response(resp)
            if resp.ok:
                data = resp.json()
                st.session_state["token"] = data.get("access_token")
                st.success("Token saved in session.")
        except Exception as exc:
            st.error(f"Login failed: {exc}")

if st.session_state.get("token"):
    st.info("Authenticated session token is set.")
else:
    st.warning("No auth token yet. Register/login first.")

st.markdown("---")

# Contract analysis
st.subheader("2) Analyze contract text")
contract_text = st.text_area(
    "Contract text",
    value="This agreement includes payment terms, confidentiality obligations, and termination conditions.",
    height=180,
)
response_language = st.selectbox("Response language", ["english", "arabic"], index=0)

if st.button("Analyze contract text"):
    try:
        resp = _post(
            "/genai/analyze-contract-text",
            {"contract_text": contract_text, "response_language": response_language},
        )
        _render_response(resp)
        if resp.ok:
            st.session_state["last_clauses"] = resp.json().get("clauses", {})
    except Exception as exc:
        st.error(f"Analyze failed: {exc}")

st.markdown("---")

st.subheader("3) Evaluate clauses")
clauses_default = st.session_state.get("last_clauses", {
    "Payment Terms Clause": "Payment due in 30 days.",
    "Confidentiality Clause": "Parties must keep data confidential.",
})
clauses_text = st.text_area("Clauses JSON", value=json.dumps(clauses_default, indent=2), height=220)

if st.button("Evaluate contract"):
    try:
        payload = {"clauses": json.loads(clauses_text), "response_language": response_language}
        resp = _post("/genai/evaluate-contract", payload)
        _render_response(resp)
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON: {exc}")
    except Exception as exc:
        st.error(f"Evaluate failed: {exc}")

st.markdown("---")

st.subheader("Quick links")
st.markdown(f"- Backend health: `{PUBLIC_API_BASE_URL}/healthz`")
st.markdown("- Frontend UI: `http://localhost:8501`")
