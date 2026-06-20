"""Index creation and seed data — the migration script, present from day one.

Run standalone with ``python -m backend.migrations`` or automatically at app
startup. Every index here backs a real query pattern in the routers; nothing is
left to full-collection scans.
"""
from __future__ import annotations

import asyncio
import logging

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.config import get_settings
from backend.constants import grade_from_score  # noqa: F401  (kept for parity/imports)
from backend.models.common import utcnow

logger = logging.getLogger(__name__)

# (collection, keys, options)
INDEXES: list[tuple[str, list[tuple[str, int]], dict]] = [
    ("users", [("username", pymongo.ASCENDING)], {"unique": True, "name": "uq_username"}),
    ("users", [("email", pymongo.ASCENDING)], {"unique": True, "name": "uq_email"}),
    ("refresh_tokens", [("token_hash", pymongo.ASCENDING)], {"unique": True, "name": "uq_refresh_hash"}),
    ("refresh_tokens", [("user_id", pymongo.ASCENDING)], {"name": "ix_refresh_user"}),
    ("refresh_tokens", [("expires_at", pymongo.ASCENDING)], {"expireAfterSeconds": 0, "name": "ttl_refresh"}),
    ("password_reset_tokens", [("token_hash", pymongo.ASCENDING)], {"unique": True, "name": "uq_reset_hash"}),
    ("password_reset_tokens", [("expires_at", pymongo.ASCENDING)], {"expireAfterSeconds": 0, "name": "ttl_reset"}),
    ("login_attempts", [("key", pymongo.ASCENDING), ("ts", pymongo.DESCENDING)], {"name": "ix_login_key_ts"}),
    ("login_attempts", [("ts", pymongo.ASCENDING)],
     {"expireAfterSeconds": 3600, "name": "ttl_login_attempts"}),
    ("clients", [("created_by", pymongo.ASCENDING)], {"name": "ix_clients_owner"}),
    ("clients", [("created_by", pymongo.ASCENDING), ("name", pymongo.ASCENDING)], {"name": "ix_clients_owner_name"}),
    ("contracts", [("created_by", pymongo.ASCENDING)], {"name": "ix_contracts_owner"}),
    ("contracts", [("created_by", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
     {"name": "ix_contracts_owner_created"}),
    ("contracts", [("created_by", pymongo.ASCENDING), ("contract_type", pymongo.ASCENDING)],
     {"name": "ix_contracts_owner_type"}),
    ("contracts", [("client_id", pymongo.ASCENDING)], {"name": "ix_contracts_client"}),
    ("contract_analyses", [("contract_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
     {"name": "ix_analyses_contract_created"}),
    ("contract_analyses", [("created_by", pymongo.ASCENDING)], {"name": "ix_analyses_owner"}),
    ("benchmark_standards", [("contract_type", pymongo.ASCENDING), ("region", pymongo.ASCENDING)],
     {"unique": True, "name": "uq_standard_type_region"}),
    ("benchmark_results", [("contract_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
     {"name": "ix_benchmark_contract_created"}),
    ("benchmark_results", [("created_by", pymongo.ASCENDING)], {"name": "ix_benchmark_owner"}),
    ("chat_messages", [("contract_id", pymongo.ASCENDING), ("created_at", pymongo.ASCENDING)],
     {"name": "ix_chat_contract_created"}),
    ("logs", [("created_at", pymongo.DESCENDING)], {"name": "ix_logs_created"}),
    ("logs", [("user_id", pymongo.ASCENDING)], {"name": "ix_logs_user"}),
    ("logs", [("action", pymongo.ASCENDING)], {"name": "ix_logs_action"}),
]


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    for collection, keys, options in INDEXES:
        try:
            await db[collection].create_index(keys, **options)
        except Exception as exc:  # pragma: no cover - depends on server capabilities
            logger.warning("Could not create index %s on %s: %s",
                           options.get("name"), collection, exc)


async def seed_benchmark_standards(db: AsyncIOMotorDatabase) -> int:
    """Idempotently seed the single benchmark knowledge base. Returns count inserted."""
    from backend.services.benchmark_seed import BENCHMARK_STANDARDS

    inserted = 0
    for standard in BENCHMARK_STANDARDS:
        result = await db.benchmark_standards.update_one(
            {"contract_type": standard["contract_type"], "region": standard["region"]},
            {"$setOnInsert": {**standard, "created_at": utcnow()}},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
    return inserted


async def run_migrations(db: AsyncIOMotorDatabase, *, seed: bool = True) -> None:
    await ensure_indexes(db)
    if seed:
        try:
            count = await seed_benchmark_standards(db)
            if count:
                logger.info("Seeded %d benchmark standards", count)
        except Exception as exc:  # pragma: no cover
            logger.warning("Benchmark seed skipped: %s", exc)


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)
    from backend.database import apply_validators, connect_to_mongo

    settings = get_settings()
    db = await connect_to_mongo()
    logger.info("Connected to %s/%s", settings.mongodb_url, settings.mongodb_db)
    await apply_validators(db)
    await run_migrations(db)
    logger.info("Migrations complete.")


if __name__ == "__main__":
    asyncio.run(_main())
