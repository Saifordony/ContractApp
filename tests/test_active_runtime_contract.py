from pathlib import Path


def test_streamlit_page_config_precedes_session_state_initialization():
    source = Path("frontend/streamlit_app.py").read_text()
    assert source.count("st.set_page_config(") == 1
    assert source.index("st.set_page_config(") < source.index("def init_state():")
    assert "Frontend Build: {FRONTEND_BUILD}" in source
    assert "streamlit-clean-rebuild-v1" in source


def test_healthz_exposes_active_backend_marker():
    source = Path("backend/routers/health.py").read_text()
    assert '"Active Backend"' in source
    assert '"Active Backend File"' in source
    assert '"Backend Build"' in source
    assert "llm_reachable" in source
    assert "fastapi-clean-rebuild-v1" in Path("backend/config.py").read_text()


def test_analysis_endpoints_use_canonical_analysis_service():
    source = Path("backend/routers/analysis.py").read_text()
    assert "from backend.services.analysis_service import analyze_text, extract_text" in source
    assert "return analyze_text(" in source
    assert "extract_text(" in source


def test_contract_analysis_chat_and_init_use_official_services():
    source = Path("backend/routers/contracts.py").read_text()
    assert "from backend.services.analysis_service import analyze_contract_record" in source
    assert "from backend.services.chat_service import chat_with_contract" in source
    assert "from backend.services.benchmark_service import benchmark_contract" in source
    assert "await analyze_contract_record(" in source
    assert "await chat_with_contract(" in source
    assert "await benchmark_contract(" in source


def test_benchmark_routes_use_official_service():
    source = Path("backend/routers/benchmark.py").read_text()
    assert "from backend.services.benchmark_service import benchmark_analysis, benchmark_contract" in source
    assert "await benchmark_contract(" in source
    assert "benchmark_analysis(" in source


def test_next_frontend_is_archived_not_active():
    assert Path("_archive/frontend-next-unused").is_dir()
    assert not Path("frontend-next").exists()
