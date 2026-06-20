# Contract Analysis Platform

A from-scratch contract intelligence platform: upload a contract (PDF / DOCX /
pasted text) and get grounded clause extraction, a contract health score, a
source-cited chat, benchmark comparison, and real PDF/CSV/JSON export — all in a
contract-first three-pane workspace, bilingual (English / العربية).

Stack: **FastAPI + MongoDB (Motor) + local Llama 3.1 via Ollama** on the backend,
**Next.js (App Router) + TypeScript + Tailwind** on the frontend.

## What it does

| Feature | Notes |
|---|---|
| Clause extraction | termination, liability, confidentiality, payment, renewal, IP, governing law, dispute resolution, indemnification, force majeure — each with status, plain-language explanation, grounded evidence, and a confidence score |
| Health score | 0–100 with clarity / risk / completeness / enforceability sub-scores, each backed by evidence |
| Chat | free-form Q&A; every answer cites the exact source text it is grounded in |
| Benchmark | compares the contract against typical terms for its type/region, returning a grade and specific gaps |
| Export | real PDF (reportlab), CSV, and JSON downloads |
| Repository | clients + contracts CRUD, scoped per user, searchable/filterable |
| Auth | register, login (rate-limited), refresh-token rotation, real logout, wired password reset |
| Bilingual | EN/AR across extraction, chat, and the UI (with RTL) |

## Architecture principles

- **One implementation per feature.** A single grounded engine
  (`backend/services/ai_pipeline.py`) powers extraction, health, chat, and
  benchmark. There is one benchmark engine and one frontend.
- **No silent degradation.** If Ollama is unreachable, the same response shape
  comes back with `degraded: true` and the UI shows a banner — a degraded answer
  never looks like a real one.
- **Evidence-grounded.** Every LLM result quotes exact source spans, which are
  verified against the document; ungrounded output is re-prompted once and
  demoted to *needs review*. A confidence score is shown on every result.
- **Schema-validated Mongo from day one**, real `ObjectId` references, indexes
  for every query pattern, and server-side aggregation for stats.
- **Streaming (SSE)** for analyze / chat / benchmark so a slow local model shows
  live progress, not a 30–180s spinner.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- [Ollama](https://ollama.com) running on the host with the model pulled:

```bash
ollama pull llama3.1:8b
```

> The backend reaches Ollama at `http://host.docker.internal:11434/v1` by default.
> On Linux this is provided via the compose `extra_hosts` mapping.

## Quick start (Docker)

```bash
cp .env.example .env          # optional: edit SECRET_KEY etc.
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API + docs: http://localhost:8000/api and http://localhost:8000/docs

Register an account in the UI, paste or upload a contract, then click **Analyze**.

## Local development (without Docker)

**Backend**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
# point MONGODB_URL at a running MongoDB; set OLLAMA_BASE_URL if not default
export $(grep -v '^#' .env.example | xargs)   # or create a real .env
python -m backend.migrations                  # create indexes + seed benchmarks
uvicorn backend.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api" > .env.local
npm run dev   # http://localhost:3000
```

## Environment variables

All backend config is environment-driven (see `.env.example`). Key ones:

| Variable | Default | Purpose |
|---|---|---|
| `MONGODB_URL` | `mongodb://localhost:27017` | Mongo connection string |
| `SECRET_KEY` | `dev-secret-key-change-me` | JWT signing key — **change in prod** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | access-token lifetime |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama OpenAI-compatible URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | model name (swap for a stronger one, no code change) |
| `OLLAMA_TEMPERATURE` / `OLLAMA_NUM_CTX` / `OLLAMA_TIMEOUT` | `0.1` / `8192` / `120` | generation + retrieval-budget config |
| `CORS_ORIGINS` | `http://localhost:3000` | allowed frontend origins |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api` | backend URL the browser calls |

## Tests

```bash
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
pytest          # backend services + routers; LLM mocked, in-memory Mongo
```

```bash
cd frontend && npm run build   # type-checks and builds the frontend
```

## Project layout

```
backend/
  main.py config.py database.py migrations.py
  models/      pydantic schemas per domain
  routers/     auth, clients, contracts, ai (SSE), export, stats, system
  services/    ai_pipeline, chunking, retrieval, llm_client, confidence,
               document_parsing, benchmark, pdf_export, export_builders
  auth/        security (hashing, JWT, refresh rotation), rate_limit
frontend/
  app/         (auth) login/register/reset-password, workspace
  components/  ContractRepository, ContractViewer, IntelligencePanel, …
  lib/         api (typed client + SSE), types, i18n
  store/       one Zustand store (active contract / analysis / chat / benchmark)
tests/         one module per service and router
docker-compose.yml
PLAN.md        the Phase 0 design (collections, API, AI pipeline)
```

## Notes / limitations

- Arabic PDF export uses DejaVu + arabic-reshaper/python-bidi (bundled in the
  backend image). Without those, Arabic text in the PDF may not shape correctly;
  CSV/JSON exports are always UTF-8 and fully bilingual.
- The local 8B model is slow; analyze/chat/benchmark stream progress and tokens
  so the UI stays responsive.
