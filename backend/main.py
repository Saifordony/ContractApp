"""Clean FastAPI entrypoint for the Streamlit-only Contract Intelligence rebuild."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_settings
from backend.database import close_mongo_connection, connect_to_mongo
from backend.routers import analysis, auth, benchmark, chat, clients, contracts, health

APP_BUILD = "fastapi-clean-rebuild-v1"

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    print(f"Backend Build: {APP_BUILD}")
    yield
    await close_mongo_connection()

settings = get_settings()
app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()] or ["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(contracts.router)
app.include_router(analysis.router)
app.include_router(chat.router)
app.include_router(benchmark.router)
