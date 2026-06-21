from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_analysis_route_uses_background_job_polling_contract():
    contracts = read("backend/routers/contracts.py")
    frontend = read("frontend/streamlit_app.py")
    assert "BackgroundTasks" in contracts
    assert "analysis_jobs" in contracts
    assert 'status": "queued"' in contracts
    assert 'status="running"' in contracts
    assert 'status="completed"' in contracts
    assert 'analysis-jobs/{job_id}' in contracts
    assert "poll_analysis_job" in frontend
    assert 'api_request("GET", f"/contracts/{contract_id}/analysis-jobs/{job_id}"' in frontend


def test_timeout_and_fast_mode_configuration_is_wired():
    config = read("backend/config.py")
    frontend = read("frontend/streamlit_app.py")
    env = read(".env.example")
    llm = read("backend/services/llm_service.py")
    analysis = read("backend/services/analysis_service.py")
    assert "frontend_api_timeout_seconds" in config
    assert "analysis_fast_mode" in config
    assert "FRONTEND_API_TIMEOUT_SECONDS = int" in frontend
    assert "FRONTEND_API_TIMEOUT_SECONDS=300" in env
    assert "OLLAMA_TIMEOUT=300" in env
    assert "_settings_timeout" in llm and "300" in llm
    assert "skipped by ANALYSIS_FAST_MODE" in analysis
    assert "analysis_fast_mode" in analysis


def test_timeout_degrades_to_rule_based_analysis_message():
    analysis = read("backend/services/analysis_service.py")
    assert "timeout" in analysis
    assert "AI analysis timed out, so a deterministic checklist analysis was returned." in analysis
    assert "Deterministic checklist analysis was returned" in analysis
    assert "analysis_stage_timings_ms" in analysis
    assert "logger.info" in analysis
