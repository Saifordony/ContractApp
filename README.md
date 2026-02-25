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

> If you are on **Windows** and you get:
> `Error: listen tcp 127.0.0.1:11434: bind ... Only one usage of each socket address ...`
>
> it means Ollama is **already running** (port 11434 is already in use). You do **not** need to run `ollama serve` again.

### 3) Download a model

Recommended default model:
```bash
ollama pull llama3.1:8b
```

You can also try:
- `qwen2.5:7b`
- `mistral:7b`

### 4) Configure environment variables

> Important on Windows: use commands that match your shell.

#### macOS / Linux (bash/zsh)

```bash
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.1:8b
```

#### Windows PowerShell

```powershell
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:OLLAMA_MODEL="llama3.1:8b"
```

#### Windows Command Prompt (cmd.exe)

```cmd
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=llama3.1:8b
```

If backend runs in Docker but Ollama runs on your host machine, use:

- bash/zsh:
  ```bash
  export OLLAMA_BASE_URL=http://host.docker.internal:11434
  ```
- PowerShell:
  ```powershell
  $env:OLLAMA_BASE_URL="http://host.docker.internal:11434"
  ```
- cmd.exe:
  ```cmd
  set OLLAMA_BASE_URL=http://host.docker.internal:11434
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

### Check Ollama is running

```bash
curl http://localhost:11434/api/tags
```

Interpret the result:
- JSON returned with models = Ollama is ready.
- `{"models":[]}` = Ollama is running but no models are pulled yet; run `ollama pull llama3.1:8b`.

### Windows troubleshooting (port 11434)

If you want to confirm what is using the port:

```cmd
netstat -ano | findstr :11434
```

If needed, stop the process (replace `<PID>`):

```cmd
taskkill /PID <PID> /F
```

Then start Ollama again:

```cmd
ollama serve
```
