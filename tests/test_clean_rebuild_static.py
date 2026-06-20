from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text()


def test_streamlit_page_config_is_first_streamlit_command():
    src = read("frontend/streamlit_app.py")
    first = min(i for i in [src.find("st.set_page_config"), src.find("st.sidebar"), src.find("st.markdown"), src.find("st.write"), src.find("st.title")] if i >= 0)
    assert src.find("st.set_page_config") == first
    assert src.count("st.set_page_config") == 1
    assert "label.frontend_build" in src and "FRONTEND_BUILD" in src
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
        "Why it matters",
        "AI recommendation",
        "LLM request status",
    ]:
        assert token in src


def test_analysis_api_debug_and_real_contract_id_mapping():
    src = read("frontend/streamlit_app.py")
    assert "label_to_contract_id" in src
    assert "selected_contract_id" in src
    assert 'endpoint_path = f"/contracts/{cid}/analyze?explanation_language=' in src
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


def test_analysis_and_benchmark_avoid_raw_main_outputs():
    src = read("frontend/streamlit_app.py")
    assert "render_overall_visual" in src
    assert "plain_value" in src
    assert "render_action_card" in src
    assert "normalize_benchmark_response" in src
    assert "render_benchmark_results" in src
    assert "Illustrative benchmark comparison" in read("backend/services/benchmark_service.py")
    assert 'st.write(data)' not in src
    assert 'st.dataframe(evidence_rows' not in src
    assert "Raw benchmark response for debugging only" in src


def test_settings_system_health_is_professional_diagnostics_dashboard():
    src = read("frontend/streamlit_app.py")
    for token in [
        "Overall System Status",
        "Service Status",
        "AI Model Diagnostics",
        "Test AI Model",
        "AI Prompt / Parser Health",
        "Backend Endpoint Checks",
        "Database Stats",
        "Environment / Config Checks",
        "Recent Safe Errors",
        "Troubleshooting",
        "Advanced / Raw Health Response",
        "Advanced / LLM Debug",
        "Advanced / Endpoint Test Results",
        "Advanced / Environment Debug",
        "run_endpoint_checks",
        "/system/diagnostics",
        "/llm/test",
    ]:
        assert token in src


def test_backend_health_router_exposes_diagnostics_without_secrets():
    src = read("backend/routers/health.py")
    llm = read("backend/services/llm_service.py")
    for token in [
        "@router.post(\"/llm/test\")",
        "@router.get(\"/system/diagnostics\")",
        "config_checks",
        "collection_counts",
        "recent_safe_errors",
        "llm_debug_status",
        "test_llm_model",
    ]:
        assert token in src or token in llm
    assert "jwt_secret" in src
    assert "settings.jwt_secret" in src
    assert "JWT_SECRET" not in src



def test_streamlit_shell_supports_theme_language_and_modern_navigation():
    src = read("frontend/streamlit_app.py")
    css = read("frontend/styles/global_css.py")
    for token in [
        "TRANSLATIONS",
        "NAV_GROUPS",
        "render_global_css",
        "render_page_header",
        "render_empty_state",
        "st.session_state.theme",
        "st.session_state.language",
        "nav.workspace",
        "language.arabic",
        "theme.dark",
        "direction = \"rtl\"",
    ]:
        assert token in src
    for token in [
        "DARK_TOKENS",
        "LIGHT_TOKENS",
        "build_app_css",
        "--cip-bg",
        ".cip-shell-topbar",
        ".cip-brand-card",
        ".cip-nav-active",
        ".cip-empty-state",
    ]:
        assert token in css



def test_analysis_extraction_key_terms_and_pdf_report():
    analysis = read("backend/services/analysis_service.py")
    report = read("backend/services/report_service.py")
    contracts = read("backend/routers/contracts.py")
    frontend = read("frontend/streamlit_app.py")
    for token in [
        "TERM_PATTERNS",
        "_details_from_evidence",
        "_extract_key_terms",
        "key_terms",
        "monetary_amounts",
        "notice_periods",
        "risk_in_plain_english",
        "what_to_check_next",
        "completeness",
    ]:
        assert token in analysis
    for token in [
        "generate_analysis_pdf",
        "Contract Intelligence Report",
        "Key Terms Extracted",
        "Clause-by-Clause Review",
        "Evidence Appendix",
        "AI-assisted review only",
    ]:
        assert token in report
    assert '@router.get("/{contract_id}/analysis/report")' in contracts
    assert "StreamingResponse" in contracts
    for token in [
        "api_download",
        "Download PDF Report",
        "Save PDF Report",
        "render_key_terms",
        "render_clause_details",
        "Key Terms Extracted",
    ]:
        assert token in frontend
    assert "The AI review did not return a specific insight" not in frontend
    assert "Generic recommendation" not in frontend


def test_theme_contrast_score_meter_and_ai_language_controls():
    src = read("frontend/streamlit_app.py")
    css = read("frontend/styles/global_css.py")
    for token in [
        "#0F172A",
        "#111827",
        "#1E293B",
        "#F8FAFC",
        "--cip-nav-active-bg",
        "--cip-nav-active-text",
        "--cip-nav-inactive-text",
        ".cip-score-meter",
        ".cip-score-track",
        ".cip-score-fill",
        ".cip-layman-box",
    ]:
        assert token in css
    assert "cip-radial" not in css
    for token in [
        "effective_explanation_language",
        "effective_report_language",
        "label.ai_explanation_language",
        "label.report_language",
        "شرح مبسط",
        "Simple explanation",
        "render_ai_decision",
        "render_priority_action_plan",
        "review_decision",
        "priority_action_plan",
        "?report_language=",
    ]:
        assert token in src
    assert "st.dataframe" not in src


def test_analysis_service_has_decision_layer_and_arabic_layman_support():
    src = read("backend/services/analysis_service.py")
    for token in [
        "def _clause_decision",
        "def _overall_decision",
        "def _action_plan",
        "review_decision",
        "priority_action_plan",
        "must_fix_before_signing",
        "human_review_required",
        "clause_decision",
        "business_impact",
        "recommended_fix",
        "questions_to_ask",
        "explanation_language",
        "clear simple Arabic",
        "هذا البند",
    ]:
        assert token in src
    assert "The AI review did not return" not in src
    assert "No overall assessment was returned" not in src
    assert "Confirm this point during legal/business review" not in src


def test_chat_and_report_support_explanation_language():
    chat = read("backend/services/chat_service.py")
    report = read("backend/services/report_service.py")
    contracts = read("backend/routers/contracts.py")
    for token in [
        "explanation_language",
        "clear simple Arabic",
        "إجابة مبنية",
        "evidence",
    ]:
        assert token in chat
    for token in ["report_language", "language=report_language", "analysis/report"]:
        assert token in contracts
    for token in ["language: str = \"en\"", "labels", "تقرير ذكاء العقود", "AI-assisted review only"]:
        assert token in report
