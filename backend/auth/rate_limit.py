"""Mongo-backed sliding-window login rate limiter.

Persisting attempts (rather than an in-process counter) means the limit holds
across workers and restarts. A TTL index on ``ts`` reaps old rows automatically.
"""
from __future__ import annotations

from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.common import utcnow


async def count_recent_attempts(db: AsyncIOMotorDatabase, key: str, window_seconds: int) -> int:
    since = utcnow() - timedelta(seconds=window_seconds)
    return await db.login_attempts.count_documents({"key": key, "ts": {"$gte": since}})


async def record_attempt(db: AsyncIOMotorDatabase, key: str) -> None:
    await db.login_attempts.insert_one({"key": key, "ts": utcnow()})


async def clear_attempts(db: AsyncIOMotorDatabase, key: str) -> None:
    await db.login_attempts.delete_many({"key": key})
