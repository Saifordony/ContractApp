@echo off
setlocal

REM Always run from repository root (folder where this script lives one level down)
cd /d "%~dp0.."

if not exist "contract_intelligence.py" (
  echo [ERROR] Could not find contract_intelligence.py. Make sure repository is extracted correctly.
  exit /b 1
)

echo [INFO] Checking Ollama...
where ollama >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Ollama is not installed. Install from https://ollama.com/download
  exit /b 1
)

curl -s http://localhost:11434/api/tags >nul 2>nul
if errorlevel 1 (
  echo [WARN] Ollama API is not reachable on http://localhost:11434
  echo [INFO] Starting Ollama service...
  start "" ollama serve
  timeout /t 3 >nul
)

echo [INFO] Ensuring model exists (llama3.1:8b)...
ollama pull llama3.1:8b
if errorlevel 1 (
  echo [ERROR] Could not pull llama3.1:8b model.
  exit /b 1
)

set SECRET_KEY=change-me-local
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=llama3.1:8b

echo [INFO] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed. Check Python/pip installation and internet access.
  exit /b 1
)

echo [INFO] Starting backend on http://localhost:8000 ...
python contract_intelligence.py

endlocal
