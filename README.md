# Contract Intelligence Platform — Streamlit Clean Rebuild

**Branch:** `rebuild/streamlit-clean-rebuild`

This repository now has one active frontend and one active backend implementation for the MVP.

## Active runtime

- **Active frontend:** Streamlit
- **Active frontend URL:** `http://localhost:8501`
- **Active frontend entrypoint:** `frontend/streamlit_app.py`
- **Frontend build marker:** `streamlit-clean-rebuild-v1`
- **Active backend:** FastAPI
- **Active backend URL:** `http://localhost:8000`
- **Active backend entrypoint:** `backend/main.py`
- **Backend build marker:** `fastapi-clean-rebuild-v1`
- **Database:** MongoDB

`frontend-next` is archived at `_archive/frontend-next-unused` and is not served by Docker. Do not edit it for visible UI changes.

## Run with Docker

```bash
docker compose down --remove-orphans --volumes
docker compose build --no-cache
docker compose up
```

Open:

- Streamlit frontend: `http://localhost:8501`
- FastAPI health: `http://localhost:8000/healthz`
- LLM health: `http://localhost:8000/llm/health`

## Environment variables

Copy `.env.example` to `.env` and customize:

- `JWT_SECRET`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `MONGODB_URL`
- `MONGODB_DB`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `CORS_ORIGINS`
- `API_BASE_URL`

Docker sets `MONGODB_URL` to use the `mongodb` service name so the backend can connect inside the compose network.

## Auth flow

1. Streamlit displays Login/Create Account before any protected page.
2. Create Account calls `POST /auth/register` with full name, email, and password.
3. Backend normalizes email to lowercase, enforces unique email, hashes the password with bcrypt/passlib, and stores the user in MongoDB.
4. Login calls `POST /auth/login` and returns a JWT access token plus a safe user object.
5. Streamlit stores the JWT and user in `st.session_state` and sends `Authorization: Bearer <token>` for protected calls.
6. `/auth/me` validates the token. If validation fails, Streamlit clears session state and returns to login.

## Official backend endpoints

- `GET /healthz`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /clients`
- `POST /clients`
- `GET /contracts`
- `POST /contracts/upload`
- `GET /contracts/{contract_id}`
- `POST /contracts/{contract_id}/analyze`
- `POST /contracts/{contract_id}/chat`
- `POST /contracts/{contract_id}/benchmark`

## Compatibility wrappers

These endpoints remain only for older callers and delegate to official services:

- `POST /genai/analyze-contract`
- `POST /genai/analyze-contract-text`
- `POST /genai/evaluate-contract`
- `POST /genai/analyze`
- `POST /genai/contract-chat`
- `POST /benchmark/compare/{contract_id}`

## Where to edit

- Frontend UI: `frontend/streamlit_app.py`
- Frontend styles: `frontend/styles/global_css.py`
- Backend app setup: `backend/main.py`
- Backend configuration: `backend/config.py`
- Database/indexes: `backend/database.py`
- Auth/security: `backend/core/security.py`, `backend/services/auth_service.py`, `backend/routers/auth.py`
- Official analysis: `backend/services/analysis_service.py`
- Official chat: `backend/services/chat_service.py`
- Official benchmark: `backend/services/benchmark_service.py`

## Troubleshooting: changes not appearing

- Confirm Docker is running Streamlit, not Next.js: `docker compose ps` should show `frontend` on port `8501`.
- Confirm the Streamlit sidebar shows `Frontend Build: streamlit-clean-rebuild-v1`.
- Confirm `http://localhost:8000/healthz` shows `Backend Build: fastapi-clean-rebuild-v1`.
- If build markers do not update after edits, rebuild with `docker compose build --no-cache` and restart.
- Do not edit `_archive/frontend-next-unused` for active UI work.
