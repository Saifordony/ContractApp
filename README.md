# ContractApp

## Open-source LLM setup (Ollama only)

This branch uses **Ollama only** for GenAI features.

### 1) Install Ollama

- Official install page: https://ollama.com/download
- Linux quick install command:
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

### 2) Start Ollama

Run:
```bash
ollama serve
```

### 3) Download a model

Recommended default model:
```bash
ollama pull llama3.1:8b
```

You can also try:
- `qwen2.5:7b`
- `mistral:7b`

### 4) Configure environment variables

Set these before starting the backend:

```bash
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.1:8b
```

If backend runs in Docker but Ollama runs on your host machine, use:

```bash
export OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### 5) Install Python dependencies

Make sure this package is installed:

```bash
pip install langchain-ollama
```

### 6) Start your backend

Start the backend exactly as you normally do.

---

## Quick verification

Test Ollama is reachable:

```bash
curl http://localhost:11434/api/tags
```

If you get a JSON response with models, Ollama is ready.
