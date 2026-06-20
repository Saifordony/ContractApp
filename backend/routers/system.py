"""System/health endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.config import get_settings
from backend.database import get_database

router = APIRouter(tags=["system"])


async def _db_status(db: AsyncIOMotorDatabase) -> str:
    try:
        await db.command("ping")
        return "up"
    except Exception:
        try:
            await db.list_collection_names()
            return "up"
        except Exception:
            return "down"


@router.get("/health")
async def health(db: AsyncIOMotorDatabase = Depends(get_database)) -> dict:
    settings = get_settings()
    db_status = await _db_status(db)

    ai_reachable = None
    try:
        from backend.services.llm_client import ping_ollama

        ai_reachable = await ping_ollama()
    except Exception:
        ai_reachable = None  # llm client not wired yet, or check failed

    return {
        "status": "ok" if db_status == "up" else "degraded",
        "db": db_status,
        "ai": {
            "reachable": ai_reachable,
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
        },
    }
