"""MongoDB connection, JSON-schema validators, and the ``get_database`` dependency.

Validators are applied at startup so every collection has an enforced shape from
day one — this is what prevents the legacy app's "same document written in two
shapes" class of bug. Indexes and seed data live in ``migrations.py``.
"""
from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def _string_or_null(extra: dict | None = None) -> dict:
    schema = {"bsonType": ["string", "null"]}
    if extra:
        schema.update(extra)
    return schema


# JSON-schema validators per collection. ``additionalProperties`` is left default
# (permitted) so the shape can evolve, but required fields and core types are enforced.
COLLECTION_VALIDATORS: dict[str, dict] = {
    "users": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["username", "email", "hashed_password", "preferences", "created_at"],
            "properties": {
                "username": {"bsonType": "string"},
                "email": {"bsonType": "string"},
                "hashed_password": {"bsonType": "string"},
                "full_name": _string_or_null(),
                "preferences": {"bsonType": "object"},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
            },
        }
    },
    "refresh_tokens": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "token_hash", "expires_at", "revoked", "created_at"],
            "properties": {
                "user_id": {"bsonType": "objectId"},
                "token_hash": {"bsonType": "string"},
                "expires_at": {"bsonType": "date"},
                "revoked": {"bsonType": "bool"},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "password_reset_tokens": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "token_hash", "expires_at", "used", "created_at"],
            "properties": {
                "user_id": {"bsonType": "objectId"},
                "token_hash": {"bsonType": "string"},
                "expires_at": {"bsonType": "date"},
                "used": {"bsonType": "bool"},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "login_attempts": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["key", "ts"],
            "properties": {
                "key": {"bsonType": "string"},
                "ts": {"bsonType": "date"},
            },
        }
    },
    "clients": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["created_by", "name", "created_at"],
            "properties": {
                "created_by": {"bsonType": "objectId"},
                "name": {"bsonType": "string"},
                "email": _string_or_null(),
                "company": _string_or_null(),
                "notes": _string_or_null(),
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
            },
        }
    },
    "contracts": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["created_by", "title", "contract_type", "region", "language",
                         "source_format", "content", "status", "created_at"],
            "properties": {
                "created_by": {"bsonType": "objectId"},
                "client_id": {"bsonType": ["objectId", "null"]},
                "title": {"bsonType": "string"},
                "contract_type": {"bsonType": "string"},
                "region": {"bsonType": "string"},
                "language": {"enum": ["en", "ar"]},
                "source_format": {"enum": ["pdf", "docx", "text"]},
                "content": {"bsonType": "string"},
                "page_count": {"bsonType": ["int", "null"]},
                "ocr_used": {"bsonType": "bool"},
                "status": {"enum": ["uploaded", "analyzed"]},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
            },
        }
    },
    "contract_analyses": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["contract_id", "created_by", "language", "degraded", "model",
                         "confidence", "clauses", "health", "created_at"],
            "properties": {
                "contract_id": {"bsonType": "objectId"},
                "created_by": {"bsonType": "objectId"},
                "language": {"bsonType": "string"},
                "degraded": {"bsonType": "bool"},
                "model": {"bsonType": "string"},
                "confidence": {"bsonType": "double"},
                "clauses": {"bsonType": "array"},
                "health": {"bsonType": "object"},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "benchmark_standards": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["contract_type", "region", "clauses", "created_at"],
            "properties": {
                "contract_type": {"bsonType": "string"},
                "region": {"bsonType": "string"},
                "language": {"bsonType": "string"},
                "clauses": {"bsonType": "array"},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "benchmark_results": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["contract_id", "created_by", "contract_type", "region",
                         "overall_score", "grade", "degraded", "confidence", "gaps", "created_at"],
            "properties": {
                "contract_id": {"bsonType": "objectId"},
                "created_by": {"bsonType": "objectId"},
                "contract_type": {"bsonType": "string"},
                "region": {"bsonType": "string"},
                "overall_score": {"bsonType": "int"},
                "grade": {"bsonType": "string"},
                "degraded": {"bsonType": "bool"},
                "confidence": {"bsonType": "double"},
                "gaps": {"bsonType": "array"},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "chat_messages": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["contract_id", "created_by", "role", "content", "created_at"],
            "properties": {
                "contract_id": {"bsonType": "objectId"},
                "created_by": {"bsonType": "objectId"},
                "role": {"enum": ["user", "assistant"]},
                "content": {"bsonType": "string"},
                "citations": {"bsonType": "array"},
                "confidence": {"bsonType": ["double", "null"]},
                "degraded": {"bsonType": ["bool", "null"]},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "logs": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["action", "created_at"],
            "properties": {
                "user_id": {"bsonType": ["objectId", "null"]},
                "action": {"bsonType": "string"},
                "resource_type": _string_or_null(),
                "resource_id": {"bsonType": ["objectId", "null"]},
                "metadata": {"bsonType": ["object", "null"]},
                "created_at": {"bsonType": "date"},
            },
        }
    },
}

COLLECTIONS = list(COLLECTION_VALIDATORS.keys())


async def apply_validators(db: AsyncIOMotorDatabase) -> None:
    """Create each collection with its validator, or update an existing one."""
    existing = set(await db.list_collection_names())
    for name, validator in COLLECTION_VALIDATORS.items():
        try:
            if name in existing:
                await db.command({
                    "collMod": name,
                    "validator": validator,
                    "validationLevel": "moderate",
                    "validationAction": "error",
                })
            else:
                await db.create_collection(
                    name, validator=validator,
                    validationLevel="moderate", validationAction="error",
                )
        except Exception as exc:  # pragma: no cover - depends on server capabilities
            logger.warning("Could not apply validator for %s: %s", name, exc)


async def connect_to_mongo() -> AsyncIOMotorDatabase:
    global _client, _db
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongodb_url, uuidRepresentation="standard")
    _db = _client[settings.mongodb_db]
    return _db


async def close_mongo_connection() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def set_database(db: AsyncIOMotorDatabase) -> None:
    """Used by the lifespan handler and by tests to inject a database."""
    global _db
    _db = db


def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency. Overridden in tests with a mock database."""
    if _db is None:
        raise RuntimeError("Database is not initialized")
    return _db
