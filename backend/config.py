"""Runtime configuration for the clean Streamlit/FastAPI rebuild."""
from functools import lru_cache
try:
    from pydantic import BaseModel
except Exception:
    class BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

import os


class Settings(BaseModel):
    app_name: str = "Contract Intelligence Platform"
    backend_build: str = "fastapi-clean-rebuild-v1"
    active_backend: str = "FastAPI"
    active_backend_file: str = "backend/main.py"
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://admin:admin123@mongodb:27017/contract_analysis?authSource=admin")
    database_name: str = os.getenv("MONGODB_DB", "contract_analysis")
    jwt_secret: str = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "dev-secret-key-change-me"))
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", os.getenv("ALGORITHM", "HS256"))
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:8501")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    ollama_analysis_model: str = os.getenv("OLLAMA_ANALYSIS_MODEL", os.getenv("OLLAMA_MODEL", "qwen3:14b"))
    ollama_chat_model: str = os.getenv("OLLAMA_CHAT_MODEL", os.getenv("OLLAMA_MODEL", "qwen3:14b"))
    ollama_review_model: str = os.getenv("OLLAMA_REVIEW_MODEL", "deepseek-r1:14b")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
    ollama_fallback_model: str = os.getenv("OLLAMA_FALLBACK_MODEL", os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
    ollama_model: str = os.getenv("OLLAMA_MODEL", os.getenv("OLLAMA_FALLBACK_MODEL", "llama3.1:8b"))
    ollama_temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "32768"))
    ollama_timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    ollama_enable_reviewer: bool = os.getenv("OLLAMA_ENABLE_REVIEWER", "true").lower() in {"1", "true", "yes", "on"}
    ollama_enable_embeddings: bool = os.getenv("OLLAMA_ENABLE_EMBEDDINGS", "true").lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
