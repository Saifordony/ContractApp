from pathlib import Path


def test_streamlit_page_config_precedes_session_state_initialization():
    source = Path("frontend/streamlit_app.py").read_text()
    assert source.count("st.set_page_config(") == 1
    main_body = source[source.index("def main():"):]
    assert main_body.index("st.set_page_config(") < main_body.index("init_session_state()")
    assert "Active UI: Streamlit / frontend/streamlit_app.py / Build v2" in source


def test_healthz_exposes_active_backend_marker():
    source = Path("backend/routers/system.py").read_text()
    assert '"active_backend_entrypoint": "backend.main:app"' in source
    assert '"active_ai_provider": AI_PROVIDER' in source
    assert '"active_model": selected_model()' in source
    assert "llm_reachable" in source
    assert 'APP_BUILD = "Backend: FastAPI / backend/main.py / Build v2"' in Path("backend/main.py").read_text()


def test_analysis_endpoints_use_canonical_analysis_service():
    source = Path("backend/routers/genai.py").read_text()
    assert "backend.services.contract_analysis_service" in source
    assert "await analyze_contract_text(" in source
    assert "await analyze_uploaded_contract(" in source
    assert "await build_health_evaluation(" in source


def test_contract_init_and_chat_use_official_services():
    source = Path("backend/routers/contracts.py").read_text()
    assert "from backend.services.contract_analysis_service import analyze_contract_text, normalize_analysis_results" in source
    assert "await analyze_contract_text(contract" in source
    assert "build_contract_chat_response(" in source
    assert "normalize_analysis_results(" in source


def test_benchmark_routes_use_official_orchestrator():
    source = Path("backend/routers/benchmark.py").read_text()
    assert "from backend.services.benchmark_orchestrator import analyze_uploaded_benchmark, compare_saved_contract" in source
    assert "compare_saved_contract(" in source
    assert "analyze_uploaded_benchmark(" in source


def test_next_frontend_is_archived_not_active():
    assert Path("_archive/frontend-next-unused").is_dir()
    assert not Path("frontend-next").exists()
