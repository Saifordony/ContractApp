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

## Key Environment Variables
- `SECRET_KEY` (required)
- `OLLAMA_BASE_URL` (local default: `http://localhost:11434/v1`; Docker-to-host default: `http://host.docker.internal:11434/v1`)
- `OLLAMA_MODEL` (default: `llama3.1:8b`)
- `OLLAMA_TEMPERATURE` (recommended: `0.1` for deterministic contract analysis)
- `OLLAMA_NUM_CTX` (recommended: `8192` where supported)
- `OLLAMA_TIMEOUT` (recommended: `120` seconds for local model latency)
- `MONGODB_URL`
- `CORS_ORIGINS`

## Notes
- If backend runs in Docker and Ollama runs on host, use `OLLAMA_BASE_URL=http://host.docker.internal:11434/v1`.
- Recommended Ollama setup: `ollama pull llama3.1:8b`; stronger optional models include `qwen2.5:14b`, `llama3.1:70b`, `deepseek-r1:14b`, and `mistral-nemo` if installed locally.
- GenAI endpoints return `503` if Ollama is not configured/reachable.


## Docker startup conflict fix (Windows/Mac/Linux)
If you see an error like:
`Conflict. The container name "/contract_analysis_mongo" is already in use`

Use one of these options:
- Start with a unique project name (recommended):
  - `docker compose -p contractapp_dev up --build`
- Or clean previous containers first:
  - `docker compose down --remove-orphans`
  - `docker rm -f contract_analysis_mongo contract_analysis_backend contract_analysis_frontend`

This repository's compose file intentionally avoids hardcoded `container_name` values so multiple copies can run side-by-side.
