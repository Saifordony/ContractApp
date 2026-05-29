"""Centralized, safe LLM provider configuration and diagnostics."""

from __future__ import annotations

import os
from typing import Any, Dict

import requests

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").strip().lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def selected_base_url() -> str:
    return OLLAMA_BASE_URL if AI_PROVIDER == "ollama" else OPENAI_BASE_URL


def selected_model() -> str:
    return OLLAMA_MODEL if AI_PROVIDER == "ollama" else OPENAI_MODEL


def selected_api_key() -> str:
    if AI_PROVIDER == "ollama":
        return OPENAI_API_KEY or "ollama"
    return OPENAI_API_KEY


def is_genai_configured() -> bool:
    if AI_PROVIDER == "ollama":
        return bool(OLLAMA_BASE_URL.strip()) and bool(OLLAMA_MODEL.strip())
    return bool(OPENAI_API_KEY.strip()) and bool(OPENAI_MODEL.strip())


def llm_health_check() -> Dict[str, Any]:
    base_url = selected_base_url()
    model = selected_model()
    models_url = f"{base_url}/models" if base_url else ""
    status: Dict[str, Any] = {
        "ai_provider": AI_PROVIDER,
        "base_url": base_url,
        "model": model,
        "reachable": False,
        "available_models": [],
        "error": None,
    }
    if not base_url or not model:
        status["error"] = "Missing base URL or model configuration"
        return status

    try:
        headers = {}
        api_key = selected_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        response = requests.get(models_url, headers=headers, timeout=5)
        if not response.ok:
            status["error"] = f"HTTP {response.status_code} from {models_url}"
            return status
        payload = response.json()
        status["available_models"] = [
            item.get("id")
            for item in payload.get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]
        status["reachable"] = True
        return status
    except Exception as exc:
        status["error"] = str(exc)
        return status


def llm_unreachable_message() -> str:
    if AI_PROVIDER == "ollama":
        return (
            "LLM provider is set to Ollama, but the backend container cannot reach "
            f"{OLLAMA_BASE_URL}/models. Confirm Ollama is running on Windows and "
            "OLLAMA_BASE_URL is set correctly."
        )
    return (
        "LLM provider is set to OpenAI, but the backend cannot reach the configured "
        "OpenAI endpoint. Confirm OPENAI_API_KEY and OPENAI_BASE_URL settings."
    )
