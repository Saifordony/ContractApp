from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class ApiError:
    friendly_message: str
    suggested_next_step: str
    technical_detail: str
    status_code: Optional[int] = None


def friendly_error_from_exception(exc: Exception) -> ApiError:
    return ApiError(
        friendly_message="Backend is currently unavailable. Please make sure the application services are running.",
        suggested_next_step="Start Docker Compose and confirm the backend is reachable at /docs.",
        technical_detail=str(exc),
        status_code=None,
    )


def friendly_error_from_response(response: requests.Response) -> ApiError:
    detail = ""
    try:
        payload = response.json()
        detail = str(payload.get("detail") or payload)
    except Exception:
        detail = response.text[:1000]

    if response.status_code == 401:
        return ApiError("Your session expired. Please sign in again.", "Sign in again to continue.", detail, response.status_code)
    if response.status_code == 400 and "analyze" in detail.lower():
        return ApiError("Please analyze this contract first.", "Run clause extraction, then retry this action.", detail, response.status_code)
    if response.status_code == 503:
        return ApiError("The AI service is currently unavailable.", "Check Ollama/OpenAI diagnostics and try again.", detail, response.status_code)
    return ApiError("The request could not be completed.", "Please review the information and try again.", detail, response.status_code)


def request_api(
    base_url: str,
    endpoint: str,
    method: str = "GET",
    token: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
) -> tuple[Optional[requests.Response], Optional[ApiError]]:
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{base_url}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            if files:
                response = requests.post(url, headers=headers, files=files, data=data, timeout=timeout)
            else:
                headers["Content-Type"] = "application/json"
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
        elif method == "PUT":
            headers["Content-Type"] = "application/json"
            response = requests.put(url, headers=headers, json=data, timeout=timeout)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")
    except requests.exceptions.RequestException as exc:
        return None, friendly_error_from_exception(exc)

    if response.status_code >= 400:
        return response, friendly_error_from_response(response)
    return response, None


def request_json(
    base_url: str,
    endpoint: str,
    method: str = "GET",
    token: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
    retry_on_timeout: bool = True,
) -> Dict[str, Any]:
    """Call the backend and return parsed JSON, or a structured error dict.

    Adds granular handling for the failure modes the UI cares about and, when
    ``retry_on_timeout`` is set, retries once with double the timeout before
    giving up. Error dicts have the shape ``{"error": <code>, "message": <text>}``.
    """
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{base_url}{endpoint}"

    def _call(call_timeout: int) -> requests.Response:
        if method == "GET":
            return requests.get(url, headers=headers, timeout=call_timeout)
        if method == "POST":
            if files:
                return requests.post(url, headers=headers, files=files, data=data, timeout=call_timeout)
            post_headers = {**headers, "Content-Type": "application/json"}
            return requests.post(url, headers=post_headers, json=data, timeout=call_timeout)
        if method == "PUT":
            put_headers = {**headers, "Content-Type": "application/json"}
            return requests.put(url, headers=put_headers, json=data, timeout=call_timeout)
        if method == "DELETE":
            return requests.delete(url, headers=headers, timeout=call_timeout)
        raise ValueError(f"Unsupported method: {method}")

    try:
        try:
            response = _call(timeout)
        except requests.exceptions.Timeout:
            if not retry_on_timeout:
                raise
            response = _call(timeout * 2)
    except requests.exceptions.ConnectionError:
        return {
            "error": "backend_unreachable",
            "message": "Cannot connect to the application backend. Make sure the services are running.",
        }
    except requests.exceptions.Timeout:
        return {
            "error": "timeout",
            "message": "The request timed out. The AI model may be busy — please try again in a moment.",
        }
    except requests.exceptions.RequestException as exc:
        return {"error": "request_failed", "message": str(exc)}

    if response.status_code == 503:
        return {
            "error": "llm_unavailable",
            "message": "AI model is not reachable. Check Ollama is running, then retry.",
        }
    if response.status_code >= 400:
        err = friendly_error_from_response(response)
        return {"error": "http_error", "message": err.friendly_message, "status_code": response.status_code}

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {
            "error": "invalid_response",
            "message": "The backend returned an unexpected (non-JSON) response.",
        }
