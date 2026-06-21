# Project Structure — Clean Streamlit Rebuild

## Official frontend

- `frontend/streamlit_app.py` — the only active Streamlit app entrypoint and the only active visible UI.
- `frontend/styles/global_css.py` — theme and CSS helpers.
- `frontend/components/` — reserved for reusable Streamlit components.
- `frontend/pages/` — intentionally contains no active Streamlit page modules in this rebuild to avoid stale multipage navigation.

## Official backend

- `backend/main.py` — FastAPI app factory, CORS, lifespan, and router registration.
- `backend/config.py` — environment-backed settings and build marker.
- `backend/database.py` — MongoDB connection and required indexes.
- `backend/core/security.py` — bcrypt password hashing, JWT creation, and protected-user dependency.

## Official routers

- `backend/routers/auth.py`
- `backend/routers/clients.py`
- `backend/routers/contracts.py`
- `backend/routers/analysis.py` — compatibility `/genai/*` wrappers around the official analysis service.
- `backend/routers/chat.py` — compatibility `/genai/contract-chat` wrapper around the official chat service.
- `backend/routers/benchmark.py` — official benchmark compatibility route.
- `backend/routers/health.py`

## Official services

- `backend/services/auth_service.py`
- `backend/services/client_service.py`
- `backend/services/contract_service.py`
- `backend/services/analysis_service.py`
- `backend/services/chat_service.py`
- `backend/services/benchmark_service.py`
- `backend/services/llm_service.py`

Do not add parallel analysis, chat, or benchmark services unless replacing these official services.

## MongoDB collections

- `users`
- `clients`
- `contracts`
- `analyses`
- `chat_sessions`
- `benchmarks`

Every protected document stores `owner_user_id` and route/service queries filter by the authenticated user.

## Archived folders

- `_archive/frontend-next-unused` — inactive Next.js frontend, not served by Docker.
- `_archive/legacy-streamlit` — old Streamlit pages/components retained for reference only.
- `_archive/legacy-backend` — duplicate legacy backend services/routers retained for reference only.

Files in `_archive/` should not be edited for active application behavior.

## Environment examples

- `.env.local.example` — local backend/frontend development with `OLLAMA_BASE_URL=http://localhost:11434`.
- `.env.docker.example` — Docker Compose development with `OLLAMA_BASE_URL=http://host.docker.internal:11434`.

## Test hygiene

Legacy tests that reference removed modules are archived under `_archive/legacy-tests`. Active tests live under `tests/` and target the current Streamlit + FastAPI service layout.

## AI engine pipeline

The active pipeline is implemented in-place, not through duplicate services:

1. Extract text/OCR from uploaded files.
2. Normalize English/Arabic text.
3. Detect contract language and type.
4. Parse logical sections/chunks with offsets.
5. Extract bilingual clause candidates.
6. Retrieve evidence through hybrid lexical/semantic-ready RAG.
7. Build deterministic risk and clause skeletons.
8. Ask Ollama for structured JSON when available.
9. Optionally run reviewer/critic mode.
10. Validate shape before the frontend renders results.
