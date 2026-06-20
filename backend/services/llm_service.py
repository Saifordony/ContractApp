"""Ollama LLM health and structured generation helpers."""
import json
import re
from typing import Any

import requests

from backend.config import get_settings


def _ollama_base() -> str:
    return get_settings().ollama_base_url.rstrip("/").replace("/v1", "")


def llm_health() -> dict[str, Any]:
    settings = get_settings()
    try:
        response = requests.get(f"{_ollama_base()}/api/tags", timeout=2)
        return {
            "reachable": response.ok,
            "status_code": response.status_code,
            "model": settings.ollama_model,
            "ollama_url": settings.ollama_base_url,
            "error": None if response.ok else "Ollama health check failed.",
        }
    except Exception as exc:
        return {
            "reachable": False,
            "error": "Ollama is not reachable.",
            "technical_error": str(exc),
            "model": settings.ollama_model,
            "ollama_url": settings.ollama_base_url,
        }


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def generate_structured_json(prompt: str, retry_prompt: str | None = None) -> dict[str, Any]:
    """Call Ollama and parse JSON. Raises on transport/model/parse failures."""
    settings = get_settings()
    prompts = [prompt]
    if retry_prompt:
        prompts.append(retry_prompt)
    last_error: Exception | None = None
    for current_prompt in prompts:
        try:
            response = requests.post(
                f"{_ollama_base()}/api/generate",
                json={"model": settings.ollama_model, "prompt": current_prompt, "stream": False, "format": "json"},
                timeout=90,
            )
            response.raise_for_status()
            payload = response.json()
            return _extract_json(payload.get("response", "{}"))
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"LLM JSON generation failed: {last_error}")
