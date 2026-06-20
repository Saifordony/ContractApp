"""Application wiring: lifespan, CORS, exception handlers, router registration.

No business logic lives here — routers call into services.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import get_settings
from backend.database import apply_validators, close_mongo_connection, connect_to_mongo
from backend.migrations import run_migrations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await connect_to_mongo()
    try:
        await apply_validators(db)
        await run_migrations(db)
    except Exception as exc:  # never block startup on schema/index hiccups
        logger.warning("Startup schema/migration step degraded: %s", exc)
    logger.info("Backend ready.")
    yield
    await close_mongo_connection()


def _error_payload(detail, code: str) -> dict:
    return {"detail": detail, "code": code}


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
        code = getattr(exc, "code", None) or f"http_{exc.status_code}"
        return JSONResponse(status_code=exc.status_code, content=_error_payload(exc.detail, code))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "code": "validation_error"},
        )

    # Routers (Phase 1). AI / export / stats are registered in later phases.
    from backend.routers import auth, clients, contracts, system

    prefix = settings.api_prefix
    app.include_router(system.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(clients.router, prefix=prefix)
    app.include_router(contracts.router, prefix=prefix)

    # Optional routers wired in later phases — import lazily so Phase 1 runs alone.
    for module_name, attr in (("ai", "router"), ("export", "router"), ("stats", "router")):
        try:
            module = __import__(f"backend.routers.{module_name}", fromlist=[attr])
            app.include_router(getattr(module, attr), prefix=prefix)
        except ModuleNotFoundError:
            pass

    return app


app = create_app()
