# Contract Intelligence Runtime Consolidation Report

## Active Runtime Decision
- The official active frontend is Streamlit at `frontend/streamlit_app.py` and `http://localhost:8501`.
- The official active backend is FastAPI at `backend.main:app` and `http://localhost:8000`.
- The previous Next.js frontend has been archived at `_archive/frontend-next-unused` and is not active in Docker.

## Frontend Cleanup
- Fixed the Streamlit startup contract by ensuring `st.set_page_config()` is called once inside `main()` before session-state initialization or any rendering command.
- Added a visible Streamlit sidebar marker: `Active UI: Streamlit / frontend/streamlit_app.py / Build v2`.
- The sidebar also calls `/healthz` and displays the active backend build marker.

## Backend Cleanup
- Added backend build marker: `Backend: FastAPI / backend/main.py / Build v2`.
- `/healthz` now reports build, active backend entrypoint, active AI provider, active model, MongoDB status, and LLM reachability.

## Official Backend Services
- Analysis: `backend/services/contract_analysis_service.py`.
- Chat: `backend/services/contract_chat_service.py`.
- Health scoring: `backend/services/contract_health.py`.
- Benchmark: `backend/services/benchmark_orchestrator.py`.

## Compatibility Wrappers
- `/genai/analyze-contract`, `/genai/analyze-contract-text`, `/genai/evaluate-contract`, `/genai/analyze`, and `/contracts/{contract_id}/init-genai` call the canonical analysis/health service.
- `/contracts/{contract_id}/chat` and `/genai/contract-chat` use the shared chat service.
- `/benchmark/compare/{contract_id}` and `/benchmark/analyze` use the official benchmark orchestrator.

## Cleanup Notes
- Removed nested ZIP project copy clutter.
- Expanded `.gitignore` for caches, secrets, Node/Next artifacts, and ZIP files.
- Added `PROJECT_STRUCTURE.md` so future agents know exactly where visible frontend/backend changes must be made.
