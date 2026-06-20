"""Tests for schema validators and index definitions."""
from __future__ import annotations

import pytest
from mongomock_motor import AsyncMongoMockClient

from backend.database import COLLECTION_VALIDATORS, COLLECTIONS
from backend.migrations import INDEXES, ensure_indexes


def test_every_collection_has_a_validator():
    expected = {
        "users", "refresh_tokens", "password_reset_tokens", "login_attempts",
        "clients", "contracts", "contract_analyses", "benchmark_standards",
        "benchmark_results", "chat_messages", "logs",
    }
    assert expected.issubset(set(COLLECTIONS))
    for name, validator in COLLECTION_VALIDATORS.items():
        schema = validator["$jsonSchema"]
        assert schema["bsonType"] == "object"
        assert "required" in schema


def test_every_collection_has_at_least_one_index():
    indexed = {collection for collection, _keys, _opts in INDEXES}
    # Every collection that is queried by something other than _id needs an index.
    for collection in ("users", "clients", "contracts", "contract_analyses",
                       "benchmark_results", "chat_messages", "logs"):
        assert collection in indexed, f"{collection} has no index"


def test_unique_indexes_declared_for_user_identity():
    user_unique = [
        opts.get("name")
        for coll, _keys, opts in INDEXES
        if coll == "users" and opts.get("unique")
    ]
    assert "uq_username" in user_unique
    assert "uq_email" in user_unique


@pytest.mark.asyncio
async def test_ensure_indexes_runs_on_mock():
    mongo = AsyncMongoMockClient()
    db = mongo["t"]
    await ensure_indexes(db)
    # Creating a duplicate username should now fail on the unique index.
    await db.users.insert_one({"username": "x", "email": "x@x.com"})
    with pytest.raises(Exception):
        await db.users.insert_one({"username": "x", "email": "y@y.com"})
