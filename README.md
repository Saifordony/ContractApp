# Contract Analysis Platform

This repository matches the **explain-repository** branch structure and behavior, but the LLM provider is switched to **Llama via Ollama** instead of OpenAI.

## Prerequisites
- Docker Desktop
- Ollama: https://ollama.com/download
- Pulled model: `ollama pull llama3.1:8b`

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

4. (Optional but recommended) set a real app secret in `.env`:
   ```env
   SECRET_KEY=your-very-strong-random-secret
   ```
   If you skip this, Docker uses a safe development default so `docker compose down` / `up` still works out of the box.

## Local Development
```bash
pip install -r requirements.txt
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.1:8b
export SECRET_KEY=dev-secret
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal:
```bash
streamlit run frontend/streamlit_app.py --server.port 8501
```

## Key Environment Variables
- `SECRET_KEY` (required)
- `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- `OLLAMA_MODEL` (default: `llama3.1:8b`)
- `MONGODB_URL`
- `CORS_ORIGINS`

## Notes
- If backend runs in Docker and Ollama runs on host, use `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
- GenAI endpoints return `503` if Ollama is not configured/reachable.
