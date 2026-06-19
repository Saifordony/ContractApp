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
    """Create indexes the application relies on (idempotent).

    The audit found that, besides the password-reset TTL index, every query ran as
    a full collection scan -- including ``/stats/summary`` which loads up to 1000
    docs into memory. These cover the hot read paths (per-user listings, latest
    analysis per contract, log analytics) and enforce account uniqueness.

    Unique indexes can fail if duplicate documents already exist; that surfaces as
    a logged "Could not create indexes" warning at startup rather than a crash, and
    is exactly what ``backend.migrations.report_duplicate_accounts`` flags ahead of
    time so duplicates can be cleaned before the constraint is enforced.
    """
    await db.password_reset_tokens.create_index(
        "created_at", expireAfterSeconds=PASSWORD_RESET_TOKEN_TTL_SECONDS
    )

    # Account identity: one user per username / email.
    await db.users.create_index("username", unique=True)
    await db.users.create_index("email", unique=True)

    # Per-user listing of contracts and clients.
    await db.contracts.create_index("created_by")
    await db.clients.create_index("created_by")

    # "Latest analysis for this contract" is the single most common analysis query.
    await db.contract_analyses.create_index([("contract_id", 1), ("created_at", -1)])
    await db.contract_analyses.create_index("created_by")

    # Log analytics (pipeline / admin dashboards) filter by user, action and time.
    await db.logs.create_index([("user", 1), ("timestamp", -1)])
    await db.logs.create_index([("action", 1), ("timestamp", -1)])
