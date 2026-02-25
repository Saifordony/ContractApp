# ContractApp

## GenAI provider configuration

This branch now supports two providers selected by `GENAI_PROVIDER`:

- `ollama` (default)
- `openai`

### Option 1: Run with Ollama (open-source LLM)

1. Install Ollama and start it.
2. Pull a model (recommended default):
   - `ollama pull llama3.1:8b`
3. Set environment variables:
   - `GENAI_PROVIDER=ollama`
   - `OLLAMA_BASE_URL=http://localhost:11434`
   - `OLLAMA_MODEL=llama3.1:8b`
4. Install dependencies (must include `langchain-ollama`).
5. Start the backend.

If the backend runs inside Docker and Ollama runs on your host machine, set:

- `OLLAMA_BASE_URL=http://host.docker.internal:11434`

### OpenAI fallback

To use OpenAI instead:

- `GENAI_PROVIDER=openai`
- `OPENAI_API_KEY=...`
- `OPENAI_MODEL=gpt-4` (or another OpenAI model)
