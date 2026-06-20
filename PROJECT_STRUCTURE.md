# Project Structure

## Runtime services

Docker Compose runs three active services:

1. `mongodb` — MongoDB database.
2. `backend` — FastAPI from `backend.main:app` on port `8000`.
3. `frontend` — Streamlit from `frontend/streamlit_app.py` on port `8501`.

## Active frontend

Official active frontend: **Streamlit**.

Edit these files for visible UI changes:

- `frontend/streamlit_app.py` — active single-file Streamlit app and navigation shell.
- `frontend/pages/*` — Streamlit page modules.
- `frontend/components/*` — Streamlit UI components.
- `frontend/styles/*` — shared Streamlit styling.
- `frontend/services/*` — frontend API, state, formatting, and report helpers.

Important Streamlit rule: `st.set_page_config()` must be the first Streamlit command in a page and must only be called once per page. In `frontend/streamlit_app.py`, session state initialization happens after `st.set_page_config()` inside `main()`.

## Archived frontend

`_archive/frontend-next-unused` contains the previous Next.js implementation. It is not served by Docker and should not be edited for visible changes unless the project intentionally migrates Docker from Streamlit to Next.js.

## Active backend

Official active backend: **FastAPI**.

- Entry point: `backend/main.py`
- Routers: `backend/routers/*`
- Services: `backend/services/*`
- Models: `backend/models.py`
- Database/index setup: `backend/database.py`, `backend/migrations.py`

## Official backend services

- Analysis: `backend/services/contract_analysis_service.py`
  - canonical schema version: `contract-analysis.v2`
  - handles clause extraction, grounded analysis, deterministic health, degraded-mode metadata, and legacy response adapters
- Chat: `backend/services/contract_chat_service.py`
  - used by `/contracts/{contract_id}/chat` and `/genai/contract-chat`
- Health scoring: `backend/services/contract_health.py`
  - deterministic scoring source for numeric health and missing clauses
- Benchmark: `backend/services/benchmark_orchestrator.py`
  - facade used by benchmark routes
  - delegates to existing benchmark comparison/upload engines while standardizing schema/degraded fields

## Primary endpoints

- `/healthz` — backend marker, active entrypoint, AI provider/model, MongoDB status, LLM reachability
- `/llm/health` — LLM diagnostics
- `/genai/analyze-contract` — Streamlit compatibility wrapper for uploaded-file analysis
- `/genai/analyze-contract-text` — Streamlit compatibility wrapper for text analysis
- `/genai/evaluate-contract` — health compatibility wrapper
- `/genai/analyze` — grounded analysis wrapper
- `/contracts/{contract_id}/init-genai` — stored-contract analysis wrapper
- `/contracts/{contract_id}/chat` — stored-contract chat
- `/genai/contract-chat` — stateless text chat wrapper
- `/benchmark/compare/{contract_id}` — primary Streamlit benchmark endpoint
- `/benchmark/analyze` — compatibility/upload benchmark wrapper

## Canonical saved analysis shape

Saved analysis results should use:

```json
{
  "schema_version": "contract-analysis.v2",
  "structured_clauses": {},
  "clauses": {},
  "health_evaluation": {},
  "grounded_analysis": {},
  "analysis_source": "contract_analysis_service",
  "created_at": "..."
}
```

Use `normalize_analysis_results()` when reading legacy analysis records.
