# Active Runtime Audit

This audit reflects the current Streamlit + FastAPI rebuild. Older findings about duplicate Next.js/legacy services are retained only in `_archive/` and are not active runtime guidance.

## Active files
- `frontend/streamlit_app.py`
- `frontend/styles/global_css.py`
- `backend/main.py`
- `backend/routers/{auth,clients,contracts,analysis,chat,benchmark,health}.py`
- `backend/services/{analysis_service,chat_service,benchmark_service,llm_service,report_service,auth_service,client_service,contract_service}.py`

## Current risks being controlled
- Contract-processing endpoints require JWT auth.
- Uploads are extension and size validated.
- OCR has page limits and user-friendly warnings.
- Benchmark is explicitly not represented as market data.
- User-specific data is scoped by `owner_user_id`.
