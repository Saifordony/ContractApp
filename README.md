# Contract Intelligence Platform

## Active architecture

This repository currently serves the **Streamlit frontend** and **FastAPI backend**.

- **Active frontend:** Streamlit
- **Active frontend URL:** http://localhost:8501
- **Active frontend entrypoint:** `frontend/streamlit_app.py`
- **Active frontend files:**
  - `frontend/streamlit_app.py`
  - `frontend/pages/*`
  - `frontend/components/*`
  - `frontend/styles/*`
- **Active backend:** FastAPI
- **Active backend URL:** http://localhost:8000
- **Active backend entrypoint:** `backend.main:app`
- **Active backend files:**
  - `backend/main.py`
  - `backend/routers/*`
  - `backend/services/*`

`frontend-next` is archived at `_archive/frontend-next-unused` and is **not served by Docker**. Do not edit archived Next.js files for visible UI changes unless Docker is intentionally migrated to Next.js.

## Build markers

The active Streamlit sidebar shows both running build markers:

- `Active UI: Streamlit / frontend/streamlit_app.py / Build v2`
- `Backend: FastAPI / backend/main.py / Build v2`

The backend marker is also returned by:

```bash
curl http://localhost:8000/healthz
```

## Primary endpoints and compatibility wrappers

Primary backend services:

- Analysis source of truth: `backend/services/contract_analysis_service.py`
- Chat source of truth: `backend/services/contract_chat_service.py`
- Benchmark facade: `backend/services/benchmark_orchestrator.py`
- Deterministic health scoring: `backend/services/contract_health.py`

Primary/active Streamlit endpoints:

- `/genai/analyze-contract` — compatibility wrapper for uploaded-file analysis
- `/genai/analyze-contract-text` — compatibility wrapper for text analysis
- `/genai/evaluate-contract` — compatibility wrapper for canonical health evaluation
- `/contracts/{contract_id}/init-genai` — compatibility wrapper that saves canonical analysis
- `/contracts/{contract_id}/chat` — stored-contract chat using the shared chat service
- `/benchmark/compare/{contract_id}` — primary saved-contract benchmark endpoint
- `/healthz` and `/llm/health` — runtime diagnostics

Newer endpoints such as `/genai/analyze` and `/genai/contract-chat` are retained as wrappers around the same official services.

## Quick Start (Docker)

1. Copy env file:
   ```bash
   cp .env.example .env
   ```
2. Start services:
   ```bash
   docker compose up --build
   ```
3. Open:
   - Frontend: http://localhost:8501
   - Backend docs: http://localhost:8000/docs
   - Backend health: http://localhost:8000/healthz

4. Set a real app secret in `.env` for non-demo use:
   ```env
   SECRET_KEY=your-very-strong-random-secret
   ```

## Local Development

```bash
pip install -r requirements.txt
export OLLAMA_BASE_URL=http://localhost:11434/v1
export OLLAMA_MODEL=llama3.1:8b
export OLLAMA_TEMPERATURE=0.1
export OLLAMA_NUM_CTX=8192
export OLLAMA_TIMEOUT=120
export SECRET_KEY=dev-secret
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal:

```bash
streamlit run frontend/streamlit_app.py --server.port 8501
```

## Verification

```bash
docker compose down --remove-orphans
docker compose up --build --force-recreate
```

Then verify:

- http://localhost:8501 opens without `st.set_page_config` errors.
- The Streamlit sidebar displays the active frontend and backend build markers.
- http://localhost:8000/healthz returns the backend build marker, active backend entrypoint, AI provider/model, MongoDB status, and LLM reachability.
- Analysis, chat, and benchmark still work from the Streamlit UI.

## Key Environment Variables

- `SECRET_KEY` (required outside Docker dev defaults)
- `OLLAMA_BASE_URL` (local default: `http://localhost:11434/v1`; Docker-to-host default: `http://host.docker.internal:11434/v1`)
- `OLLAMA_MODEL` (default: `llama3.1:8b`)
- `OLLAMA_TEMPERATURE` (recommended: `0.1`)
- `OLLAMA_NUM_CTX` (recommended: `8192`)
- `OLLAMA_TIMEOUT` (recommended: `120` seconds)
- `MONGODB_URL`
- `CORS_ORIGINS`

## Development rules for future agents

- Do not edit `_archive/frontend-next-unused` for visible UI changes.
- Do not add new analysis/chat/benchmark services unless replacing the official service and updating all wrappers.
- Keep route files thin: validate requests, call services, return responses.
- Keep compatibility endpoints working for the Streamlit UI until Docker is intentionally migrated.
