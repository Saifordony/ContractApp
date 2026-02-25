# ContractApp

This repo now runs with **Ollama only** (no OpenAI).

## Windows quick start (recommended)

After downloading and extracting the repo, use one of these scripts from Command Prompt:

### Option A: Local Python run (no Docker)

```cmd
scripts\run_local_windows.cmd
```

This script will:
- switch to the repo folder automatically
- check Ollama
- pull `llama3.1:8b`
- install Python dependencies
- start backend on `http://localhost:8000`

### Option B: Docker run

```cmd
scripts\run_docker_windows.cmd
```

This script will:
- switch to repo folder automatically
- verify Docker Desktop is installed and running
- create `.env` from `.env.example` if missing
- run `docker compose up --build`

---

## Why your screenshot failed

1. `python: can't open file ... contract_intelligence.py`
   - You ran python **outside** the repo folder.
2. `'docker-compuse' is not recognized`
   - Typo: correct command is `docker compose`.
3. `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`
   - Docker Desktop engine is not running.

Use the scripts above to avoid these mistakes.


### Container name conflict fix

If you see an error like:
`The container name "/contract_analysis_backend" is already in use`

run:

```cmd
docker rm -f contract_analysis_backend contract_analysis_mongo
```

Then run again:

```cmd
scripts\run_docker_windows.cmd
```

---

## Manual setup (if you prefer commands)

### 1) Install Ollama

- https://ollama.com/download

### 2) Start Ollama

```cmd
ollama serve
```

If you see port `11434` already in use, Ollama is already running.

### 3) Pull model

```cmd
ollama pull llama3.1:8b
```

### 4) Verify Ollama

```cmd
curl http://localhost:11434/api/tags
```

### 5) Local Python run

```cmd
pip install -r requirements.txt
set SECRET_KEY=change-me-local
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=llama3.1:8b
python contract_intelligence.py
```

Health check:

```cmd
curl http://localhost:8000/healthz
```

### 6) Docker run

```cmd
copy .env.example .env
docker compose up --build
```

Health check:

```cmd
curl http://localhost:8000/healthz
```

---

## API smoke test

Register:

```cmd
curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d "{\"username\":\"test1\",\"email\":\"test1@example.com\",\"password\":\"pass1234\"}"
```

Login:

```cmd
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d "{\"username\":\"test1\",\"password\":\"pass1234\"}"
```

Analyze:

```cmd
curl -X POST http://localhost:8000/genai/analyze-contract-text -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d "{\"contract_text\":\"This agreement includes payment terms, confidentiality, and termination clauses.\",\"response_language\":\"english\"}"
```
