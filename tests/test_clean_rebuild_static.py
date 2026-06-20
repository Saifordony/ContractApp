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


def test_analysis_page_uses_polished_renderers_not_raw_json_main_ui():
    src = read("frontend/streamlit_app.py")
    assert "def normalize_analysis_response" in src
    assert "def render_clause_card" in src
    assert "def render_evidence" in src
    assert "def render_risk_card" in src
    assert "def render_score_cards" in src
    assert "Advanced / Debug Output" in src
    assert "Raw backend response for debugging only" in src
    assert 'st.write(data["clauses"])' not in src
    assert 'st.write(data["risks"])' not in src


def test_analysis_service_exposes_hybrid_ai_contract():
    src = read("backend/services/analysis_service.py")
    for token in [
        "llm_used",
        "ai_status",
        "AI contract review assistant",
        "generate_structured_json",
        "raw_llm_response",
        "llm_parse_failed",
        "evidence_trace",
    ]:
        assert token in src


def test_analysis_ui_shows_ai_sections_and_status():
    src = read("frontend/streamlit_app.py")
    for token in [
        "AI Status",
        "Hybrid AI + rule-based",
        "Rule-based fallback",
        "AI Executive Review",
        "AI Review by Clause",
        "AI insight",
        "AI recommendation",
        "LLM request status",
    ]:
        assert token in src


def test_analysis_api_debug_and_real_contract_id_mapping():
    src = read("frontend/streamlit_app.py")
    assert "label_to_contract_id" in src
    assert "selected_contract_id" in src
    assert 'endpoint_path = f"/contracts/{cid}/analyze"' in src
    assert "Advanced / API Debug" in src
    assert "status_code" in src
    assert "response_body" in src


def test_contract_analysis_route_logs_and_returns_contract_id():
    src = read("backend/routers/contracts.py")
    assert 'router.post("/{contract_id}/analyze")' in src
    assert "analysis route hit" in src
    assert "analysis completed" in src
    assert 'result["contract_id"] = contract_id' in src
    assert "degraded_mode" in src and "llm_used" in src


def test_chat_service_supports_conversational_contract_aware_schema():
    src = read("backend/services/chat_service.py")
    for token in [
        "classify_question",
        "contract_specific",
        "small_talk",
        "app_help",
        "plain_english_summary",
        "practical_note",
        "follow_up_suggestions",
        "used_contract",
        "You are a helpful contract intelligence assistant",
    ]:
        assert token in src


def test_chat_ui_is_chat_style_not_raw_json_main_view():
    src = read("frontend/streamlit_app.py")
    for token in [
        "st.chat_message",
        "st.chat_input",
        "chat_history",
        "render_chat_evidence",
        "Evidence used",
        "Suggested follow-ups",
        "New chat",
    ]:
        assert token in src
