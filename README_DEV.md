# Developer Notes

## Active runtime

The active app is Streamlit (`frontend/streamlit_app.py`) plus FastAPI (`backend/main.py`). Do not edit `_archive/` for active behavior.

## Running locally

```bash
cp .env.local.example .env
uvicorn backend.main:app --reload
streamlit run frontend/streamlit_app.py
```

## Running with Docker

```bash
cp .env.docker.example .env
docker compose up --build
```

Docker reaches host Ollama through `http://host.docker.internal:11434`.

## Testing

```bash
pytest -q
```

Active tests are offline-friendly and do not require live Ollama. OCR/PDF tests skip or mock optional runtime dependencies when unavailable.

## Security model

JWT auth protects clients, contracts, analysis, chat, benchmark, diagnostics, and LLM test endpoints. Public endpoints are limited to health/status probes.
