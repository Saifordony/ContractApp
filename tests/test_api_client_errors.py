"""Tests for granular error handling and timeout retry in the API client."""

import requests

from frontend.services import api_client


class _Resp:
    def __init__(self, status_code=200, json_data=None, raise_json=False):
        self.status_code = status_code
        self._json = json_data or {}
        self._raise_json = raise_json
        self.text = "body"

    def json(self):
        if self._raise_json:
            raise requests.exceptions.JSONDecodeError("no json", "doc", 0)
        return self._json


def test_connection_error_maps_to_backend_unreachable(monkeypatch):
    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(api_client.requests, "get", boom)
    result = api_client.request_json("http://x", "/stats/summary")
    assert result["error"] == "backend_unreachable"


def test_timeout_retries_once_then_succeeds(monkeypatch):
    calls = []

    def flaky(url, **kwargs):
        calls.append(kwargs.get("timeout"))
        if len(calls) == 1:
            raise requests.exceptions.Timeout("slow")
        return _Resp(200, {"ok": True})

    monkeypatch.setattr(api_client.requests, "get", flaky)
    result = api_client.request_json("http://x", "/stats/summary", timeout=10)
    assert result == {"ok": True}
    assert calls == [10, 20]  # retried with doubled timeout


def test_timeout_without_retry_returns_timeout_error(monkeypatch):
    def always_timeout(*a, **k):
        raise requests.exceptions.Timeout("slow")

    monkeypatch.setattr(api_client.requests, "get", always_timeout)
    result = api_client.request_json("http://x", "/e", retry_on_timeout=False)
    assert result["error"] == "timeout"


def test_503_maps_to_llm_unavailable(monkeypatch):
    monkeypatch.setattr(api_client.requests, "get", lambda *a, **k: _Resp(503))
    result = api_client.request_json("http://x", "/genai/analyze")
    assert result["error"] == "llm_unavailable"


def test_invalid_json_maps_to_invalid_response(monkeypatch):
    monkeypatch.setattr(api_client.requests, "get", lambda *a, **k: _Resp(200, raise_json=True))
    result = api_client.request_json("http://x", "/e")
    assert result["error"] == "invalid_response"
