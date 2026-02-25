# ContractApp

This repo now runs with **Ollama only** (no OpenAI).

## 0) Prerequisites

1. Install Ollama: https://ollama.com/download
2. Install Docker Desktop (if you want Docker run)
3. Install Git

---

## 1) First-time setup (required once)

### Start Ollama

```cmd
ollama serve
```

If you see `bind ... 11434 ... only one usage ...`, Ollama is already running (that is OK).

### Pull a model

```cmd
ollama pull llama3.1:8b
```

### Verify Ollama

```cmd
curl http://localhost:11434/api/tags
```

If you get JSON output, Ollama is available.

---

## 2) Fastest way to run (Docker)

### Step A: clone and enter repo

```cmd
git clone <your-repo-url>
cd ContractApp
```

### Step B: create env file

```cmd
copy .env.example .env
```

Edit `.env` if needed (defaults usually work on Windows Docker Desktop).

### Step C: run containers

```cmd
docker compose up --build
```

### Step D: test backend health

```cmd
curl http://localhost:8000/healthz
```

Expected: JSON with `"status":"healthy"`.

---

## 3) Run without Docker (local Python)

### Step A: install deps

```cmd
pip install -r requirements.txt
```

### Step B: set env vars in same cmd window

```cmd
set SECRET_KEY=change-me
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=llama3.1:8b
```

### Step C: run backend

```cmd
python contract_intelligence.py
```

### Step D: test health

```cmd
curl http://localhost:8000/healthz
```

---

## 4) Test GenAI endpoint quickly

1) Register user:

```cmd
curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d "{\"username\":\"test1\",\"email\":\"test1@example.com\",\"password\":\"pass1234\"}"
```

2) Login (copy `access_token`):

```cmd
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d "{\"username\":\"test1\",\"password\":\"pass1234\"}"
```

3) Call analyze endpoint:

```cmd
curl -X POST http://localhost:8000/genai/analyze-contract-text -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d "{\"contract_text\":\"This agreement includes payment terms, confidentiality, and termination clauses.\",\"response_language\":\"english\"}"
```

---

## Notes

- Docker backend is configured to reach host Ollama at:
  - `http://host.docker.internal:11434`
- Config file examples:
  - `docker-compose.yml`
  - `.env.example`
- Legacy reference compose-like sample is in `sample_contract.txt`.
