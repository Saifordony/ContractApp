"""Robust local Ollama client helpers for health, text, JSON, and embeddings."""
from __future__ import annotations

import asyncio
import json
import re
from time import perf_counter, sleep
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

try:  # httpx is declared in requirements; this fallback keeps offline tests import-safe.
    import httpx  # type: ignore
except Exception:  # pragma: no cover - exercised only in minimal environments
    httpx = None  # type: ignore

from backend.config import get_settings

LAST_LLM_DIAGNOSTIC: dict[str, Any] = {
    "last_call_successful": None,
    "last_json_parse_successful": None,
    "fallback_used": None,
    "last_fallback_reason": None,
    "last_parser_error": None,
    "last_prompt_mode": None,
    "average_response_time_ms": None,
    "model_used": None,
    "embedding_available": None,
}


def _ollama_base() -> str:
    return get_settings().ollama_base_url.rstrip("/").replace("/v1", "")


def _settings_timeout() -> float:
    return float(getattr(get_settings(), "ollama_timeout", 300))


def _setting(name: str, default: Any) -> Any:
    return getattr(get_settings(), name, default)


def _fallback_model() -> str:
    return str(_setting("ollama_model", _setting("ollama_fallback_model", "llama3.1:8b")))


def _analysis_model() -> str:
    return str(_setting("ollama_model", _setting("ollama_analysis_model", _fallback_model())))


def _chat_model() -> str:
    return str(_setting("ollama_model", _setting("ollama_chat_model", _fallback_model())))


def _review_model() -> str:
    return str(_setting("ollama_review_model", _fallback_model()))


def _embed_model() -> str:
    return str(_setting("ollama_embed_model", ""))


def _extract_model_names(payload: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in payload.get("models", []) if isinstance(payload, dict) else []:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return names


def _sync_json_request(path: str, payload: dict[str, Any] | None = None, timeout: float | None = None) -> dict[str, Any]:
    url = f"{_ollama_base()}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlrequest.urlopen(req, timeout=timeout or _settings_timeout()) as response:  # nosec - local configurable Ollama URL
        raw = response.read().decode("utf-8", errors="replace")
        return json.loads(raw or "{}")


async def _async_json_request(path: str, payload: dict[str, Any] | None = None, timeout: float | None = None) -> dict[str, Any]:
    if httpx is None:
        return await asyncio.to_thread(_sync_json_request, path, payload, timeout)
    async with httpx.AsyncClient(timeout=timeout or _settings_timeout()) as client:
        if payload is None:
            response = await client.get(f"{_ollama_base()}{path}")
        else:
            response = await client.post(f"{_ollama_base()}{path}", json=payload)
        response.raise_for_status()
        return response.json()


def list_ollama_models() -> list[str]:
    try:
        return _extract_model_names(_sync_json_request("/api/tags", timeout=3))
    except Exception:
        return []


async def list_ollama_models_async() -> list[str]:
    try:
        return _extract_model_names(await _async_json_request("/api/tags", timeout=3))
    except Exception:
        return []


def check_model_available(model_name: str | None) -> bool:
    return bool(model_name and model_name in set(list_ollama_models()))


async def check_model_available_async(model_name: str | None) -> bool:
    return bool(model_name and model_name in set(await list_ollama_models_async()))


def select_available_model(preferred: str | None, fallback: str | None = None, installed: list[str] | None = None) -> dict[str, Any]:
    installed = installed if installed is not None else list_ollama_models()
    preferred = preferred or fallback
    if preferred and preferred in installed:
        return {"model": preferred, "available": True, "fallback_used": False, "installed_models": installed}
    if fallback and fallback in installed:
        return {"model": fallback, "available": True, "fallback_used": True, "preferred_unavailable": preferred, "installed_models": installed}
    return {"model": fallback or preferred or "", "available": False, "fallback_used": bool(fallback and fallback != preferred), "preferred_unavailable": preferred, "installed_models": installed}


def _model_for_task(task: str) -> str:
    settings = get_settings()
    fallback = _fallback_model()
    mapping = {
        "analysis": _analysis_model(),
        "chat": _chat_model(),
        "review": _review_model(),
        "embedding": _embed_model(),
    }
    selected = select_available_model(mapping.get(task, fallback), fallback if task != "embedding" else mapping.get(task), list_ollama_models())
    return selected.get("model") or fallback


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _repair_json_text(text: str) -> str:
    match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
    if not match:
        return "{}"
    candidate = match.group(0).strip().replace("\ufeff", "")
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    return candidate


async def generate_text(prompt: str, model: str | None = None, task: str = "chat", temperature: float | None = None, timeout: float | None = None) -> dict[str, Any]:
    settings = get_settings()
    model = model or _model_for_task(task)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature if temperature is not None else _setting("ollama_temperature", 0.1), "num_ctx": _setting("ollama_num_ctx", 32768)},
    }
    last_error: Exception | None = None
    started = perf_counter()
    for attempt in range(2):
        try:
            body = await _async_json_request("/api/generate", payload, timeout=timeout)
            elapsed = int((perf_counter() - started) * 1000)
            LAST_LLM_DIAGNOSTIC.update({"last_call_successful": True, "fallback_used": False, "average_response_time_ms": elapsed, "model_used": model})
            return {"ok": True, "text": str(body.get("response", "")), "model_used": model, "latency_ms": elapsed, "degraded_mode": False}
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.25 * (attempt + 1))
    LAST_LLM_DIAGNOSTIC.update({"last_call_successful": False, "fallback_used": True, "last_fallback_reason": str(last_error), "model_used": model})
    return {"ok": False, "text": "", "model_used": model, "safe_error": "Ollama text generation is unavailable.", "technical_error": str(last_error), "degraded_mode": True}


def generate_text_sync(prompt: str, model: str | None = None, task: str = "chat", temperature: float | None = None, timeout: float | None = None) -> dict[str, Any]:
    try:
        return asyncio.run(generate_text(prompt, model=model, task=task, temperature=temperature, timeout=timeout))
    except RuntimeError:
        # If called from a running loop, fall back to a direct sync request.
        settings = get_settings()
        model = model or _model_for_task(task)
        payload = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": temperature if temperature is not None else _setting("ollama_temperature", 0.1), "num_ctx": _setting("ollama_num_ctx", 32768)}}
        try:
            body = _sync_json_request("/api/generate", payload, timeout=timeout)
            return {"ok": True, "text": str(body.get("response", "")), "model_used": model, "degraded_mode": False}
        except Exception as exc:
            return {"ok": False, "text": "", "model_used": model, "safe_error": "Ollama text generation is unavailable.", "technical_error": str(exc), "degraded_mode": True}


async def generate_json(prompt: str, model: str | None = None, task: str = "analysis", retry_prompt: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    model = model or _model_for_task(task)
    prompts = [prompt] + ([retry_prompt] if retry_prompt else [])
    LAST_LLM_DIAGNOSTIC.update({"last_prompt_mode": task, "last_call_successful": False, "last_json_parse_successful": False, "fallback_used": False, "last_fallback_reason": None, "model_used": model})
    last_error: Exception | None = None
    started = perf_counter()
    for current_prompt in prompts:
        payload = {
            "model": model,
            "prompt": current_prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": _setting("ollama_temperature", 0.1), "num_ctx": _setting("ollama_num_ctx", 32768)},
        }
        try:
            body = await _async_json_request("/api/generate", payload)
            raw = str(body.get("response", "{}"))
            try:
                parsed = _extract_json(raw)
            except Exception:
                parsed = _extract_json(_repair_json_text(raw))
            elapsed = int((perf_counter() - started) * 1000)
            LAST_LLM_DIAGNOSTIC.update({"last_call_successful": True, "last_json_parse_successful": True, "average_response_time_ms": elapsed, "last_parser_error": None, "model_used": model})
            return parsed
        except Exception as exc:
            last_error = exc
            LAST_LLM_DIAGNOSTIC.update({"last_parser_error": str(exc), "last_fallback_reason": "LLM JSON generation or parsing failed", "fallback_used": True})
            await asyncio.sleep(0.2)
    raise RuntimeError(f"LLM JSON generation failed: {last_error}")


def generate_structured_json(prompt: str, retry_prompt: str | None = None, prompt_mode: str = "analysis", model: str | None = None) -> dict[str, Any]:
    try:
        return asyncio.run(generate_json(prompt, model=model, task=prompt_mode, retry_prompt=retry_prompt))
    except RuntimeError as exc:
        if "asyncio.run" not in str(exc):
            raise
        raise RuntimeError("generate_structured_json must be called outside the active event loop or via asyncio.to_thread.") from exc


async def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    if not bool(_setting("ollama_enable_embeddings", True)):
        return []
    model = model or _embed_model()
    embeddings: list[list[float]] = []
    for text in texts:
        try:
            body = await _async_json_request("/api/embeddings", {"model": model, "prompt": text[:8000]}, timeout=_setting("ollama_timeout", 300))
            vector = body.get("embedding") or []
            embeddings.append([float(x) for x in vector] if isinstance(vector, list) else [])
        except Exception:
            LAST_LLM_DIAGNOSTIC.update({"embedding_available": False, "fallback_used": True, "last_fallback_reason": "Embedding generation failed"})
            return []
    LAST_LLM_DIAGNOSTIC.update({"embedding_available": bool(embeddings)})
    return embeddings


def embed_text(text: str, model: str | None = None) -> list[float]:
    vectors = asyncio.run(embed_texts([text], model=model))
    return vectors[0] if vectors else []


def embed_texts_sync(texts: list[str], model: str | None = None) -> list[list[float]]:
    try:
        return asyncio.run(embed_texts(texts, model=model))
    except RuntimeError:
        return []


def llm_health() -> dict[str, Any]:
    return health_check()


def health_check() -> dict[str, Any]:
    settings = get_settings()
    if not bool(_setting("ollama_enabled", True)):
        return {
            "reachable": False,
            "status": "disabled",
            "degraded": True,
            "base_url": settings.ollama_base_url,
            "ollama_url": settings.ollama_base_url,
            "installed_models": [],
            "analysis_model": {"model": _analysis_model(), "available": False},
            "chat_model": {"model": _chat_model(), "available": False},
            "review_model": {"model": _review_model(), "available": False},
            "embedding_model": {"model": _embed_model(), "available": False},
            "embedding_available": False,
            "reviewer_enabled": False,
            "reviewer_available": False,
            "model": _fallback_model(),
            "error": "Ollama is disabled by OLLAMA_ENABLED=false.",
        }
    started = perf_counter()
    try:
        models = list_ollama_models()
        latency = int((perf_counter() - started) * 1000)
        analysis = select_available_model(_analysis_model(), _fallback_model(), models)
        chat = select_available_model(_chat_model(), _fallback_model(), models)
        reviewer = select_available_model(_review_model(), _fallback_model(), models)
        embedding = select_available_model(_embed_model(), _embed_model(), models)
        return {
            "reachable": True,
            "status": "available" if models else "degraded",
            "degraded": not bool(models),
            "base_url": settings.ollama_base_url,
            "ollama_url": settings.ollama_base_url,
            "latency_ms": latency,
            "installed_models": models,
            "analysis_model": analysis,
            "chat_model": chat,
            "review_model": reviewer,
            "embedding_model": embedding,
            "embedding_available": bool(embedding.get("available")) and bool(_setting("ollama_enable_embeddings", True)),
            "reviewer_enabled": bool(_setting("ollama_enable_reviewer", False)),
            "reviewer_available": bool(reviewer.get("available")) and bool(_setting("ollama_enable_reviewer", False)),
            "model": _fallback_model(),
            "error": None,
        }
    except Exception as exc:
        return {
            "reachable": False,
            "status": "unavailable",
            "degraded": True,
            "base_url": settings.ollama_base_url,
            "ollama_url": settings.ollama_base_url,
            "error": "Ollama is not reachable.",
            "technical_error": str(exc),
            "analysis_model": {"model": _analysis_model(), "available": False},
            "chat_model": {"model": _chat_model(), "available": False},
            "review_model": {"model": _review_model(), "available": False},
            "embedding_model": {"model": _embed_model(), "available": False},
            "embedding_available": False,
            "reviewer_enabled": bool(_setting("ollama_enable_reviewer", False)),
            "reviewer_available": False,
            "model": _fallback_model(),
        }


def llm_debug_status() -> dict[str, Any]:
    return dict(LAST_LLM_DIAGNOSTIC)


def test_llm_model() -> dict[str, Any]:
    started = perf_counter()
    result = generate_text_sync("Reply with one short sentence: diagnostics ok", model=_chat_model(), task="chat", timeout=30)
    elapsed = int((perf_counter() - started) * 1000)
    if not result.get("ok"):
        return {"ok": False, "model": result.get("model_used"), "response_time_ms": elapsed, "safe_error": result.get("safe_error"), "technical_error": result.get("technical_error")}
    return {"ok": True, "model": result.get("model_used"), "response_time_ms": elapsed, "sample_response": result.get("text", "").strip()[:240]}
