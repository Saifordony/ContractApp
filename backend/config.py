"""Runtime configuration for the clean Streamlit/FastAPI rebuild."""
from functools import lru_cache
from pydantic import BaseModel
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
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


@lru_cache
def get_settings() -> Settings:
    return Settings()
