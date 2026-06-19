"""MongoDB connection and index setup.

``backend.main`` owns the live ``db`` / ``db_client`` globals (tests monkeypatch
``backend.main.db`` directly to inject an in-memory fake), so this module only
holds the pure, easily-testable pieces: building a client and declaring indexes.
"""

import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

# Password-reset tokens auto-expire after 1 hour.
PASSWORD_RESET_TOKEN_TTL_SECONDS = 3600


def create_mongo_client(url: str = MONGODB_URL) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(url)


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create indexes the application relies on (idempotent)."""
    await db.password_reset_tokens.create_index(
        "created_at", expireAfterSeconds=PASSWORD_RESET_TOKEN_TTL_SECONDS
    )
