"""Audit logging with a single consistent ``<domain>_<verb>`` action vocabulary."""
from __future__ import annotations

import logging
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.common import utcnow

logger = logging.getLogger(__name__)


async def record_log(
    db: AsyncIOMotorDatabase,
    action: str,
    *,
    user_id: Optional[ObjectId] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[ObjectId] = None,
    metadata: Optional[dict] = None,
) -> None:
    doc = {
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "metadata": metadata,
        "created_at": utcnow(),
    }
    try:
        await db.logs.insert_one(doc)
    except Exception as exc:  # logging must never break a request
        logger.warning("Failed to write audit log %s: %s", action, exc)
