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

## Local vs Docker Ollama setup

Use `.env.local.example` when running the backend directly on your machine:

```bash
cp .env.local.example .env
# OLLAMA_BASE_URL=http://localhost:11434
```

Use `.env.docker.example` with Docker Compose when Ollama runs on the host:

```bash
cp .env.docker.example .env
# OLLAMA_BASE_URL=http://host.docker.internal:11434
```

`docker-compose.yml` already uses the Docker-safe `host.docker.internal` default and declares the host gateway mapping.

## Upload, OCR, and Arabic support

Supported uploads are PDF, DOCX, TXT, PNG, JPG, and JPEG up to 20 MB. PDFs are text-extracted first; if little or no text is found, the backend attempts OCR for scanned pages with Tesseract using English + Arabic language packs. Missing OCR dependencies produce warnings/errors instead of silent failures.

## AI engine pipeline

The active engine normalizes extracted text, detects language, detects contract type, parses sections, extracts bilingual clauses, retrieves evidence, scores contract health by contract type, and optionally asks local Ollama to enrich the analysis. If Ollama is unavailable or returns malformed JSON, deterministic degraded-mode output is returned.

## Benchmark limitation

Benchmark results are **template alignment and contract completeness comparisons** using internal checklist profiles. They are **not live market data** and are not legal market benchmarks.

## Smarter local Ollama engine

The active AI engine is still fully local-Ollama friendly. It now separates model roles so you can run a light setup on smaller machines or a stronger setup on workstations with more memory.

### Recommended model pull

Linux/macOS:

```bash
scripts/pull_ollama_models.sh
```

Windows PowerShell:

```powershell
scripts\pull_ollama_models.ps1
```

The stable MVP needs only one local model:

- `llama3.1:8b` for optional wording improvements in analysis and chat

The helper scripts also leave commented examples for larger models, but embeddings, reviewer models, and multi-model RAG are future enhancements, not part of the active stable runtime.

### Ollama model configuration

Recommended stable setup:

```env
AI_MODE=simple
OLLAMA_ENABLED=true
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=60
ANALYSIS_JOB_TIMEOUT_SECONDS=180
```

To run without Ollama, set `OLLAMA_ENABLED=false`. The backend will still return deterministic bilingual checklist analysis and evidence-based chat responses.

### Simple AI mode and degraded mode

Contract analysis now follows a stable evidence-first pipeline: extraction/OCR, normalization, language and contract-type detection, section-aware chunking, bilingual clause extraction, deterministic risk/checklist scoring, and one optional Ollama call to improve wording. Ollama is never the source of truth and never controls whether analysis completes.

`GET /llm/health` shows whether Ollama is enabled/reachable and which single model is configured. Safe health endpoints remain public, while contract-processing AI endpoints require authentication.

Benchmarking is an internal template-alignment/completeness comparison, not live market or legal-market data.

### Analysis jobs and timeout behavior

`POST /contracts/{contract_id}/analyze` now starts a background analysis job and returns a `job_id` instead of holding the browser request open for the full Ollama run. Streamlit polls `GET /contracts/{contract_id}/analysis-jobs/{job_id}` until the job is completed or failed. This prevents local-model analysis from surfacing as a frontend request timeout.

Timeout-related settings:

```env
FRONTEND_API_TIMEOUT_SECONDS=300
OLLAMA_TIMEOUT=60
ANALYSIS_JOB_TIMEOUT_SECONDS=180
ANALYSIS_FAST_MODE=true
```

For slow machines, keep `ANALYSIS_FAST_MODE=true` or set `OLLAMA_ENABLED=false`. The backend will still return deterministic checklist analysis if Ollama is unavailable or times out.

Simple Docker setup:

```powershell
ollama pull llama3.1:8b
docker compose up --build
```
