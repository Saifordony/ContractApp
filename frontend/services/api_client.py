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
