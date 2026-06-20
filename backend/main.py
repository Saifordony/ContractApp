"""FastAPI application entrypoint: config, auth/session primitives, and router wiring.

Route handlers live in ``backend/routers/*.py``. Each router reads this module back
via ``from backend import main as _main`` (not ``from backend.main import db``) so
request handlers always see the live ``db`` / ``db_client`` globals -- including the
in-memory fakes tests swap in after import.
"""

import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.database import create_mongo_client, ensure_indexes
from backend.gen1 import llm_model
from backend.llm_config import (
    AI_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    is_genai_configured,
    llm_health_check,
    selected_base_url,
    selected_model,
)

# Load environment variables
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
if not is_genai_configured():
    print("WARNING: LLM configuration incomplete. GenAI features will be disabled.")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
BENCHMARK_ENABLED = os.getenv("BENCHMARK_ENABLED", "true").lower() == "true"

# Build marker: surfaced unauthenticated at GET /healthz and rendered in the
# frontend sidebar. Bump this string to confirm at a glance that the running
# process is serving the current code (the dev-loop sanity beacon).
APP_BUILD = "Backend: FastAPI / backend/main.py / Build v2"

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable must be set")

# Global variables
db_client = None
db = None

# Security
pwd_context = CryptContext(schemes=["bcrypt", "pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()


# Database setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_client, db
    db_client = create_mongo_client()
    db = db_client.contract_analysis

    # Test connections
    try:
        await db_client.admin.command("ping")
        print("Database connections established")
    except Exception as e:
        print(f"Database connection failed: {e}")

    try:
        await ensure_indexes(db)
    except Exception as e:
        print(f"Could not create indexes: {e}")
    print(
        f"LLM startup config: provider={AI_PROVIDER}, "
        f"model={selected_model()}, base_url={selected_base_url()}"
    )
    llm_status = llm_health_check()
    print(
        "LLM startup health: "
        f"reachable={llm_status.get('reachable')}, "
        f"model_count={len(llm_status.get('available_models', []))}, "
        f"error={llm_status.get('error')}"
    )

    yield

    # Shutdown
    if db_client:
        db_client.close()


app = FastAPI(
    title="Contract Analysis Platform",
    description="GenAI-powered contract analysis platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def parse_object_id(value: str, field_name: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc


def build_report_context_from_results(results: Dict[str, Any]) -> str:
    """Build concise textual context from saved analysis results for report-aware chat."""
    if not isinstance(results, dict) or not results:
        return ""

    health = results.get("health_evaluation", results)
    lines = ["ANALYSIS REPORT SUMMARY:"]

    if isinstance(health, dict):
        lines.append(f"approved: {health.get('approved')}")
        if health.get("health_score") is not None:
            lines.append(f"health_score: {health.get('health_score')}/100")
        if health.get("risk_level"):
            lines.append(f"risk_level: {health.get('risk_level')}")
        if health.get("contract_type"):
            lines.append(f"contract_type: {health.get('contract_type')}")

        missing = health.get("missing_critical_clauses", [])
        if isinstance(missing, list) and missing:
            lines.append("missing_critical_clauses: " + ", ".join(str(x) for x in missing[:8]))

        changes = health.get("required_changes", [])
        if isinstance(changes, list) and changes:
            lines.append("required_changes: " + " | ".join(str(x) for x in changes[:5]))

    clauses = results.get("clauses", {})
    if isinstance(clauses, dict) and clauses:
        lines.append("extracted_clause_titles: " + ", ".join(list(clauses.keys())[:20]))

    return "\n".join(lines)


def ensure_benchmark_enabled() -> None:
    if not BENCHMARK_ENABLED:
        raise HTTPException(status_code=404, detail="Benchmark feature is disabled")


def log_analysis_llm_context(route: str) -> Dict[str, Any]:
    health = llm_health_check()
    print(
        f"{route}: USING VALIDATED CLAUSE EXTRACTION PIPELINE; "
        f"AI_PROVIDER={AI_PROVIDER}; "
        f"OLLAMA_BASE_URL={OLLAMA_BASE_URL}; "
        f"OLLAMA_MODEL={OLLAMA_MODEL}; "
        f"llm_reachable={health.get('reachable')}"
    )
    return health


def generate_benchmark_ai_commentary(payload: Dict[str, Any]) -> str:
    prompt = (
        "You are a contract benchmark analyst. Compare the uploaded contract only against "
        "the provided benchmark rules, baseline data, and extracted evidence. Do not invent "
        "averages, market values, or legal requirements. If no benchmark dataset exists, clearly "
        "state that the comparison is rule-based. Return a short, professional, user-friendly "
        "interpretation in plain English.\n\nBenchmark payload:\n"
        + json.dumps(payload, ensure_ascii=False)[:12000]
    )
    result = llm_model.invoke(prompt).content
    return str(result).strip()


def format_analysis_error(exc: Exception, health: Optional[Dict[str, Any]] = None) -> str:
    if health and health.get("reachable") is False:
        return (
            f"LLM provider is set to {health.get('ai_provider')}, but the backend cannot reach "
            f"{health.get('base_url')}/models. Error: {health.get('error')}"
        )
    message = str(exc) or exc.__class__.__name__
    if "json" in message.lower() or "parse" in message.lower():
        return f"Model response parsing failed: {message}"
    return f"Analysis failed: {exc.__class__.__name__}: {message}"


# Authentication utilities
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.users.find_one({"username": username})
    if user is None:
        raise credentials_exception
    return user


def _score_bucket(score: Any) -> Optional[str]:
    """Bucket a 0-100 health score into high/medium/low (None if not numeric)."""
    try:
        value = float(score)
    except (TypeError, ValueError):
        return None
    if value >= 75:
        return "high"
    if value >= 50:
        return "medium"
    return "low"


def _clause_difference_summary(
    clause_type: str, status_a: str, text_a: str, status_b: str, text_b: str
) -> str:
    """Plain-English description of how a clause differs between two contracts.

    Deterministic by design so comparison never depends on a reachable LLM; an
    Ollama-backed summary can be layered on top where configured.
    """
    label = clause_type.replace("_", " ")
    if status_a == "found" and status_b != "found":
        return f"Contract A defines {label}, but Contract B does not."
    if status_b == "found" and status_a != "found":
        return f"Contract B defines {label}, but Contract A does not."
    if status_a != "found" and status_b != "found":
        return f"Neither contract clearly defines {label}."
    a_norm = " ".join((text_a or "").split())
    b_norm = " ".join((text_b or "").split())
    if a_norm == b_norm:
        return f"Both contracts define {label} with effectively identical wording."
    return f"Both contracts define {label}, but the wording differs and should be compared clause by clause."


# Routers are imported after the shared primitives above (app, get_current_user,
# db/db_client globals, helpers) so their ``Depends(_main.get_current_user)`` defaults
# and ``_main.X`` lookups resolve against a fully-initialized module. Some test suites
# reimport backend.main by popping it from sys.modules without evicting the cached
# backend.routers.* submodules; without forcing those to reimport too, their
# ``_main`` reference (and anything captured via ``Depends(_main.get_current_user)``)
# would keep pointing at a stale, earlier module instance.
#
# Each router does ``from backend import main as _main``, which resolves via the
# ``backend`` package's ``main`` attribute. The import system only refreshes that
# attribute *after* a ``backend.main`` import fully completes -- too late for routers
# (re)imported from within this still-executing module -- so set it explicitly first.
#
# Popping a router from sys.modules is not enough on its own, either: CPython's
# ``from backend.routers import contracts`` (IMPORT_FROM) is handled by
# ``_handle_fromlist``, which skips reimporting ``contracts`` entirely if
# ``backend.routers`` (the parent package object) still has a ``contracts``
# attribute from the previous import -- even though that attribute's sys.modules
# entry was just removed. So the stale attribute has to be cleared on the parent
# package object too, or the "reimport" below is a no-op that silently rebinds to
# the old module.
import backend as _backend_pkg
import backend.routers as _routers_pkg

_backend_pkg.main = sys.modules[__name__]

for _router_name in (
    "auth",
    "genai",
    "clients",
    "contracts",
    "benchmark",
    "pipeline",
    "stats",
    "system",
):
    sys.modules.pop(f"backend.routers.{_router_name}", None)
    _routers_pkg.__dict__.pop(_router_name, None)

from backend.routers import auth, benchmark, clients, contracts, genai, pipeline, stats, system  # noqa: E402

app.include_router(auth.router)
app.include_router(genai.router)
app.include_router(clients.router)
app.include_router(contracts.router)
app.include_router(benchmark.router)
app.include_router(pipeline.router)
app.include_router(stats.router)
app.include_router(system.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
