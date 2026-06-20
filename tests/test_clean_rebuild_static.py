from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text()


def test_streamlit_page_config_is_first_streamlit_command():
    src = read("frontend/streamlit_app.py")
    first = min(i for i in [src.find("st.set_page_config"), src.find("st.sidebar"), src.find("st.markdown"), src.find("st.write"), src.find("st.title")] if i >= 0)
    assert src.find("st.set_page_config") == first
    assert src.count("st.set_page_config") == 1
    assert "Frontend Build: {FRONTEND_BUILD}" in src
    assert "streamlit-clean-rebuild-v1" in src


def test_backend_health_marker_contract():
    src = read("backend/routers/health.py")
    assert '"Active Backend"' in src
    assert '"Active Backend File"' in src
    assert '"Backend Build"' in src
    assert "fastapi-clean-rebuild-v1" in read("backend/config.py")


def test_official_services_and_routes_exist():
    for path in [
        "backend/services/auth_service.py",
        "backend/services/client_service.py",
        "backend/services/contract_service.py",
        "backend/services/analysis_service.py",
        "backend/services/chat_service.py",
        "backend/services/benchmark_service.py",
        "backend/services/llm_service.py",
        "backend/routers/auth.py",
        "backend/routers/clients.py",
        "backend/routers/contracts.py",
        "backend/routers/analysis.py",
        "backend/routers/chat.py",
        "backend/routers/benchmark.py",
        "backend/routers/health.py",
    ]:
        assert (ROOT / path).exists(), path


def test_auth_security_contract():
    security = read("backend/core/security.py")
    auth = read("backend/services/auth_service.py")
    assert 'schemes=["bcrypt"]' in security
    assert "create_access_token" in security
    assert "email.strip().lower()" in auth
    assert "Incorrect email or password" in auth


def test_compatibility_endpoints_delegate_to_official_services():
    analysis = read("backend/routers/analysis.py")
    chat = read("backend/routers/chat.py")
    benchmark = read("backend/routers/benchmark.py")
    assert '/analyze-contract' in analysis and "analyze_text" in analysis
    assert '/analyze-contract-text' in analysis and '/evaluate-contract' in analysis and '/analyze' in analysis
    assert '/contract-chat' in chat and "answer_question" in chat
    assert '/compare/{contract_id}' in benchmark and "benchmark_contract" in benchmark


def test_next_frontend_not_active():
    assert not (ROOT / "frontend-next").exists()
    assert (ROOT / "_archive/frontend-next-unused").exists()


def test_streamlit_ui_feedback_not_used_in_ternaries_or_one_line_blocks():
    src = read("frontend/streamlit_app.py")
    forbidden = [
        " if ok else st.",
        " else st.",
        "if ok: st.",
        "; st.success",
        "; st.error",
        "; st.warning",
        "; st.info",
        "border=True",
    ]
    for pattern in forbidden:
        assert pattern not in src
