"""Async Ollama client (OpenAI-compatible API).

One thin client used by the entire pipeline. Supports blocking completion (JSON
mode), token streaming, and a reachability ping. Any transport/parse failure is
surfaced as ``LLMUnavailable`` so callers can switch to the degraded path with a
visible flag rather than silently changing behavior.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Optional

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)


class LLMUnavailable(Exception):
    """Raised when the LLM cannot be reached or returns an unusable response."""


class LLMClient:
    def __init__(self, *, base_url: str, model: str, api_key: str,
                 temperature: float, num_ctx: int, timeout: int):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.timeout = timeout

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _body(self, messages: list[dict], *, stream: bool, json_mode: bool,
              max_tokens: Optional[int], temperature: Optional[float]) -> dict:
        body: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "stream": stream,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if max_tokens:
            body["max_tokens"] = max_tokens
        return body

    async def complete(self, messages: list[dict], *, json_mode: bool = False,
                       max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        body = self._body(messages, stream=False, json_mode=json_mode,
                          max_tokens=max_tokens, temperature=temperature)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/chat/completions",
                                         json=body, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
            return data["choices"][0]["message"]["content"] or ""
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
            logger.warning("LLM complete failed: %s", exc)
            raise LLMUnavailable(str(exc)) from exc

    async def stream(self, messages: list[dict], *, max_tokens: Optional[int] = None,
                     temperature: Optional[float] = None) -> AsyncIterator[str]:
        body = self._body(messages, stream=True, json_mode=False,
                          max_tokens=max_tokens, temperature=temperature)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", f"{self.base_url}/chat/completions",
                                         json=body, headers=self._headers()) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content")
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                        if delta:
                            yield delta
        except httpx.HTTPError as exc:
            logger.warning("LLM stream failed: %s", exc)
            raise LLMUnavailable(str(exc)) from exc

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 5)) as client:
                resp = await client.get(f"{self.base_url}/models", headers=self._headers())
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        api_key=settings.ollama_api_key,
        temperature=settings.ollama_temperature,
        num_ctx=settings.ollama_num_ctx,
        timeout=settings.ollama_timeout,
    )


async def ping_ollama() -> bool:
    return await get_llm_client().ping()
