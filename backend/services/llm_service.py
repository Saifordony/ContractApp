"""Ollama LLM health and structured generation helpers."""
import json
import re
from time import perf_counter
from typing import Any

import requests

from backend.config import get_settings

LAST_LLM_DIAGNOSTIC: dict[str, Any] = {"last_call_successful": None, "last_json_parse_successful": None, "fallback_used": None, "last_fallback_reason": None, "last_parser_error": None, "last_prompt_mode": None, "average_response_time_ms": None}


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


def generate_structured_json(prompt: str, retry_prompt: str | None = None, prompt_mode: str = "analysis") -> dict[str, Any]:
    """Call Ollama and parse JSON. Raises on transport/model/parse failures."""
    settings = get_settings()
    prompts = [prompt]
    LAST_LLM_DIAGNOSTIC.update({"last_prompt_mode": prompt_mode, "last_call_successful": False, "last_json_parse_successful": False, "fallback_used": False, "last_fallback_reason": None})
    started = perf_counter()
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
            parsed = _extract_json(payload.get("response", "{}"))
            elapsed = int((perf_counter() - started) * 1000)
            LAST_LLM_DIAGNOSTIC.update({"last_call_successful": True, "last_json_parse_successful": True, "average_response_time_ms": elapsed, "last_parser_error": None})
            return parsed
        except Exception as exc:
            last_error = exc
            LAST_LLM_DIAGNOSTIC.update({"last_parser_error": str(exc), "last_fallback_reason": "LLM JSON generation or parsing failed", "fallback_used": True})
    raise RuntimeError(f"LLM JSON generation failed: {last_error}")


def llm_debug_status() -> dict[str, Any]:
    return dict(LAST_LLM_DIAGNOSTIC)


def test_llm_model() -> dict[str, Any]:
    settings = get_settings()
    started = perf_counter()
    try:
        response = requests.post(
            f"{_ollama_base()}/api/generate",
            json={"model": settings.ollama_model, "prompt": "Reply with one short sentence: diagnostics ok", "stream": False},
            timeout=30,
        )
        elapsed = int((perf_counter() - started) * 1000)
        if not response.ok:
            return {"ok": False, "model": settings.ollama_model, "response_time_ms": elapsed, "safe_error": "Ollama test request failed.", "status_code": response.status_code}
        body = response.json()
        return {"ok": True, "model": settings.ollama_model, "response_time_ms": elapsed, "sample_response": body.get("response", "").strip()[:240]}
    except Exception as exc:
        return {"ok": False, "model": settings.ollama_model, "response_time_ms": None, "safe_error": "Ollama test request could not complete.", "technical_error": str(exc)}
