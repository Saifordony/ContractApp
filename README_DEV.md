# README_DEV

## Assumptions and implementation notes

1. **No UI/styling changes** were introduced in this round; all changes are backend/service/test focused.
2. **Groundedness policy**: contract Q&A and health outputs are produced only from extracted contract text chunks and include evidence quotes + locations.
3. **Deterministic schemas**: service-layer outputs use fixed JSON keys for downstream reliability.
4. **Pipeline Analysis is separate from Contract Health**:
   - Pipeline Analysis = sales/delivery opportunity funnel metrics.
   - Contract Health = legal/commercial risk and contract quality dimensions.
5. **Page references** are not always available after plain-text extraction; therefore evidence locations use section labels and character offset ranges.
6. **Self-test mode** supports offline deterministic checks even when API is unavailable; if API is reachable, it additionally runs full API flow tests.
7. Existing environment variable behavior is preserved (`SECRET_KEY` remains required at startup with clear runtime error if missing).

## Ollama troubleshooting (Docker backend on Windows host)

Required environment variables for Docker Compose backend:
- `AI_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://host.docker.internal:11434/v1`
- `OLLAMA_MODEL=llama3.1:8b`
- `OLLAMA_TEMPERATURE=0.1`
- `OLLAMA_NUM_CTX=8192`
- `OLLAMA_TIMEOUT=120`
- `OPENAI_API_KEY=ollama`

Recommended local model setup:
- `ollama pull llama3.1:8b` (safe default)
- Optional stronger local models if your machine has enough RAM/VRAM: `ollama pull qwen2.5:14b`, `ollama pull llama3.1:70b`, `ollama pull deepseek-r1:14b`, or `ollama pull mistral-nemo`

From Windows host (PowerShell):
- `curl.exe http://localhost:11434/v1/models`

From inside backend container:
- `python -c "import requests; print(requests.get('http://host.docker.internal:11434/v1/models', timeout=10).text)"`


## Benchmark Comparison feature

### Feature flag
- `BENCHMARK_ENABLED=true` enables `/benchmark/*` APIs and the Streamlit Benchmark page.
- `BENCHMARK_ENABLED=false` hides/blocks benchmark functionality.

### Seed benchmark corpus
- Seed file: `tests/fixtures/benchmark_seed.json`
- Ingest via API (admin/dev account or `BENCHMARK_ALLOW_ALL_INGEST=true`):
  - `POST /benchmark/ingest` with JSON `{"use_repo_seed": true}`

### Run tests
- `PYTHONPATH=contract-analysis-platform pytest -q contract-analysis-platform/tests`

### Run self-test
- `PYTHONPATH=contract-analysis-platform python -m backend.selftest`

### OCR setup for scanned English/Arabic contracts

The app supports text PDFs, scanned PDFs, DOCX, TXT, PNG, JPG, and JPEG uploads. Normal text extraction runs first; if the text is empty or too short, OCR is used when enabled.

Install the Python dependencies from `requirements.txt`, then install the Tesseract binary and language packs:

**Ubuntu / Debian**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-ara
```

**macOS**
```bash
brew install tesseract tesseract-lang
```

**Windows**
- Install Tesseract OCR from the official Windows installer.
- Add the Tesseract install directory to `PATH`.
- Confirm Arabic (`ara`) and English (`eng`) trained-data files are installed.

OCR language selection:
- English UI: `eng+ara`
- Arabic UI: `ara+eng`

If OCR dependencies are missing, the app returns a friendly message instead of failing silently. Low-quality scans may show a warning that extracted text may be inaccurate.
