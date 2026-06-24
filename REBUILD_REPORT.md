# Contract Intelligence Runtime Stabilization Report

## Active runtime
- Frontend: `frontend/streamlit_app.py` (Streamlit only).
- Styles: `frontend/styles/global_css.py`.
- Backend: `backend/main.py` with routers under `backend/routers/`.
- Canonical services: `backend/services/analysis_service.py`, `chat_service.py`, `benchmark_service.py`, `llm_service.py`, `report_service.py`, auth/client/contract services.
- Archived code lives under `_archive/` and is not part of active runtime.

## AI engine pipeline
The active analysis pipeline now follows: file extraction/OCR metadata -> text normalization -> language detection -> contract-type detection -> section parsing -> bilingual clause extraction -> deterministic scoring -> optional Ollama reasoning over evidence -> safe fallback.

## Security
Contract-processing compatibility endpoints under `/genai/*`, benchmark processing, `/llm/test`, and official contract analysis/chat/benchmark endpoints require JWT auth. Public endpoints are limited to safe health/status checks such as `/healthz`, `/readyz`, and `/llm/health`.

## OCR and Arabic
Upload extraction supports PDF/DOCX/TXT and image uploads (PNG/JPG/JPEG). PDFs use text extraction first and OCR fallback with Tesseract for scanned pages. OCR language defaults to `eng+ara` or `ara+eng` depending on requested language. Arabic clause detection is implemented for source Arabic text, not just translated output.

## Benchmark
Benchmark is framed as template alignment and contract completeness comparison. It is an internal checklist comparison, not market/legal market data.
