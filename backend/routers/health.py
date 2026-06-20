from datetime import datetime, timezone
from fastapi import APIRouter
from backend.config import get_settings
from backend import database
from backend.services.llm_service import llm_health

router = APIRouter(tags=["health"])

@router.get("/healthz")
async def healthz():
    settings = get_settings()
    mongo = "unknown"
    try:
        if database.db is not None:
            await database.db.command("ping")
            mongo = "connected"
        else:
            mongo = "not_connected"
    except Exception:
        mongo = "unreachable"
    llm = llm_health()
    return {"Active Backend": settings.active_backend, "Active Backend File": settings.active_backend_file, "Backend Build": settings.backend_build, "mongodb_status": mongo, "auth_status": "enabled", "llm_ollama_status": "reachable" if llm.get("reachable") else "unreachable", "active_model": settings.ollama_model, "timestamp": datetime.now(timezone.utc).isoformat()}

@router.get("/llm/health")
def llm_status():
    return llm_health()
