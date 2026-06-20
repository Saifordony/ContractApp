"""Consistent API error type carrying a machine-readable ``code``."""
from __future__ import annotations

from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(self, status_code: int, detail: str, code: str):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


def not_found(resource: str = "Resource") -> ApiError:
    return ApiError(404, f"{resource} not found", "not_found")


def forbidden(detail: str = "Not permitted") -> ApiError:
    return ApiError(403, detail, "forbidden")
