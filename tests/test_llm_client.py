"""Tests for the Ollama client using an injected mock transport."""
from __future__ import annotations

import httpx
import pytest

from backend.services.llm_client import LLMClient, LLMUnavailable


def _client(handler) -> LLMClient:
    return LLMClient(
        base_url="http://ollama/v1", model="m", api_key="k",
        temperature=0.1, num_ctx=8192, timeout=10,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_complete_returns_content():
    def handler(_request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}]})

    result = await _client(handler).complete([{"role": "user", "content": "hi"}])
    assert result == "hello"


@pytest.mark.asyncio
async def test_complete_raises_on_server_error():
    def handler(_request):
        return httpx.Response(500, text="boom")

    with pytest.raises(LLMUnavailable):
        await _client(handler).complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_stream_yields_tokens():
    def handler(_request):
        body = (
            'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(200, text=body)

    tokens = [t async for t in _client(handler).stream([{"role": "user", "content": "hi"}])]
    assert "".join(tokens) == "Hello"


@pytest.mark.asyncio
async def test_ping():
    assert await _client(lambda _r: httpx.Response(200, json={"data": []})).ping() is True
    assert await _client(lambda _r: httpx.Response(503)).ping() is False
