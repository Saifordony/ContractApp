import os
import requests
import streamlit as st

st.set_page_config(page_title="ContractApp", layout="centered")

st.title("ContractApp Frontend")

api_base = os.getenv("API_BASE_URL", "http://backend:8000").rstrip("/")
st.caption(f"Backend: {api_base}")

if st.button("Check backend health"):
    try:
        resp = requests.get(f"{api_base}/healthz", timeout=10)
        st.write(resp.status_code)
        st.json(resp.json())
    except Exception as exc:
        st.error(f"Failed to reach backend: {exc}")

st.markdown("---")
st.subheader("Quick notes")
st.markdown("- Backend API: `http://localhost:8000`\n- Frontend UI: `http://localhost:8501`")
