"""Shared FastAPI dependencies (current-user resolution)."""
from __future__ import annotations

from bson import ObjectId
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.auth.security import decode_token
from backend.database import get_database
from backend.errors import ApiError

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    if credentials is None:
        raise ApiError(401, "Not authenticated", "unauthorized")
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise ApiError(401, "Invalid or expired token", "invalid_token")
    sub = payload.get("sub")
    if not sub or not ObjectId.is_valid(sub):
        raise ApiError(401, "Invalid token subject", "invalid_token")
    user = await db.users.find_one({"_id": ObjectId(sub)})
    if user is None:
        raise ApiError(401, "User no longer exists", "unauthorized")
    return user
