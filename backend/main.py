from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, status, Query, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorClient
from concurrent.futures import ThreadPoolExecutor
from bson import ObjectId
from bson.errors import InvalidId
import os
import json
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from backend.gen1 import (
    analyze_contract,
    evaluate_contract,
    extract_text_from_pdf_bytes,
    extract_text_from_upload_bytes,
    analyze_and_evaluate_contract,
    explain_clauses_for_layman,
    llm_model,
)
from backend.services.contract_intelligence import extract_key_clauses
from backend.services.contract_health import evaluate_contract_health_from_clauses
from backend.services.benchmark_baselines import run_benchmark
from backend.services.pipeline_analysis import analyze_pipeline
from backend.services.benchmark_service import (
    ingest_seed_dataset,
    load_seed_from_repo,
    run_benchmark_analysis,
)
from backend.services.contract_chat_service import build_contract_chat_response, classify_chat_intent
from backend.services.benchmark_comparison_service import build_benchmark_comparison
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
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
BENCHMARK_ENABLED = os.getenv("BENCHMARK_ENABLED", "true").lower() == "true"

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable must be set")

# Global variables
db_client = None
db = None
executor = ThreadPoolExecutor()

# Security
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()


# Pydantic models
class User(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Client(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None


class Contract(BaseModel):
    title: str
    client_id: str
    content: Optional[str] = None
    status: str = "pending"


class ContractAnalysis(BaseModel):
    contract_id: str
    clauses: Dict[str, str]
    evaluation: Dict[str, Any]
    created_at: datetime




class ContractTextAnalysisRequest(BaseModel):
    contract_text: str
    response_language: str = "english"

class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ContractChatRequest(BaseModel):
    message: Optional[str] = None
    question: Optional[str] = None
    chat_history: list[ChatHistoryMessage] = []
    response_language: str = "english"
    response_mode: str = "ask_anything"
    debug: bool = False


class PipelineOpportunity(BaseModel):
    client: str
    opportunity_name: str
    stage: str
    value: float
    expected_close_date: Optional[str] = None
    last_updated: Optional[str] = None
    owner: Optional[str] = None
    close_target: Optional[float] = 0


class PipelineAnalysisRequest(BaseModel):
    opportunities: list[PipelineOpportunity]
    stage_probabilities: Optional[Dict[str, float]] = None


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class ContractCompareRequest(BaseModel):
    contract_id_a: str
    contract_id_b: str


# Database setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_client, db
    db_client = AsyncIOMotorClient(MONGODB_URL)
    db = db_client.contract_analysis

    # Test connections
    try:
        await db_client.admin.command("ping")
        print("Database connections established")
    except Exception as e:
        print(f"Database connection failed: {e}")

    # Password-reset tokens auto-expire after 1 hour via a TTL index on created_at.
    try:
        await db.password_reset_tokens.create_index("created_at", expireAfterSeconds=3600)
    except Exception as e:
        print(f"Could not create password_reset_tokens TTL index: {e}")
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


# API Endpoints


# Authentication endpoints
@app.post("/auth/register")
async def register(user: User):
    existing_user = await db.users.find_one(
        {"$or": [{"username": user.username}, {"email": user.email}]}
    )
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Username or email already registered"
        )

    hashed_password = get_password_hash(user.password)
    user_dict = {
        "username": user.username,
        "email": user.email,
        "password": hashed_password,
        "created_at": datetime.utcnow(),
    }

    result = await db.users.insert_one(user_dict)
    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id),
    }


@app.post("/auth/login")
async def login(user: UserLogin):
    db_user = await db.users.find_one({"username": user.username})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# GenAI Contract Analysis endpoints
@app.post("/genai/analyze-contract")
async def analyze_contract_endpoint(
    file: UploadFile = File(...),
    response_language: str = Form("english"),
    use_ocr: bool = Form(True),
    current_user: dict = Depends(get_current_user),
):
    allowed_extensions = (".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg")
    if not file.filename or not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Supported files: PDF, DOCX, TXT, PNG, JPG, and JPEG")

    if not is_genai_configured():
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: Ollama not configured",
        )

    analysis_health = None
    try:
        file_bytes = await file.read()
        extracted = extract_text_from_upload_bytes(
            file_bytes,
            file.filename,
            content_type=file.content_type,
            use_ocr=use_ocr,
            response_language=response_language,
        )
        contract_text = extracted["text"]
        analysis_health = log_analysis_llm_context("/genai/analyze-contract")
        structured_clauses = extract_key_clauses(contract_text)
        found_clauses = {
            k: v.get("extracted_text")
            for k, v in structured_clauses.get("clauses", {}).items()
            if isinstance(v, dict) and v.get("status") == "found" and v.get("extracted_text")
        }
        clause_explanations = (
            await explain_clauses_for_layman(found_clauses, response_language=response_language)
            if found_clauses
            else {}
        )

        # Log the action
        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/analyze-contract",
                "action": "contract_analysis",
                "timestamp": datetime.utcnow(),
                "status": "success",
            }
        )

        ocr_warning = None
        if extracted.get("used_ocr") and extracted.get("ocr_confidence") is not None and extracted.get("ocr_confidence", 1) < 0.45:
            ocr_warning = "جودة المسح منخفضة، لذلك قد يكون بعض النص المستخرج غير دقيق." if response_language.lower().startswith("ar") else "The scan quality is low, so some extracted text may be inaccurate."
        return {
            "structured_clauses": structured_clauses,
            "clause_explanations": clause_explanations,
            "contract_text": contract_text,
            "used_ocr": bool(extracted.get("used_ocr")),
            "ocr_confidence": extracted.get("ocr_confidence"),
            "ocr_warning": ocr_warning,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/analyze-contract",
                "action": "contract_analysis",
                "timestamp": datetime.utcnow(),
                "status": "error",
                "error": str(e),
            }
        )
        print(f"/genai/analyze-contract failed: {e}")
        raise HTTPException(status_code=500, detail=format_analysis_error(e, analysis_health))




@app.post("/genai/analyze-contract-text")
async def analyze_contract_text_endpoint(
    payload: ContractTextAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    if not is_genai_configured():
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: Ollama not configured",
        )

    contract_text = (payload.contract_text or "").strip()
    if len(contract_text) < 100:
        raise HTTPException(status_code=422, detail="Contract text is too short to analyze.")

    analysis_health = None
    try:
        analysis_health = log_analysis_llm_context("/genai/analyze-contract-text")
        structured_clauses = extract_key_clauses(contract_text)
        found_clauses = {
            k: v.get("extracted_text")
            for k, v in structured_clauses.get("clauses", {}).items()
            if isinstance(v, dict) and v.get("status") == "found" and v.get("extracted_text")
        }
        clause_explanations = (
            await explain_clauses_for_layman(found_clauses, response_language=payload.response_language)
            if found_clauses
            else {}
        )

        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/analyze-contract-text",
                "action": "contract_analysis_text",
                "timestamp": datetime.utcnow(),
                "status": "success",
                "chunk_count": structured_clauses.get("chunk_count", 0),
                "conflicts_count": len(structured_clauses.get("conflicts", [])),
            }
        )
        return {
            "structured_clauses": structured_clauses,
            "clause_explanations": clause_explanations,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/analyze-contract-text",
                "action": "contract_analysis_text",
                "timestamp": datetime.utcnow(),
                "status": "error",
                "error": str(e),
            }
        )
        print(f"/genai/analyze-contract-text failed: {e}")
        raise HTTPException(status_code=500, detail=format_analysis_error(e, analysis_health))

@app.post("/genai/evaluate-contract")
async def evaluate_contract_endpoint(
    payload: Dict[str, Any], current_user: dict = Depends(get_current_user)
):
    if not is_genai_configured():
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: Ollama not configured",
        )

    try:
        clauses = payload.get("clauses", payload)
        response_language = payload.get("response_language", "english")

        llm_evaluation = await evaluate_contract(
            clauses,
            response_language=response_language,
        )
        rule_evaluation = evaluate_contract_health_from_clauses(clauses, response_language=response_language)

        evaluation = {
            **llm_evaluation,
            **rule_evaluation,
            "llm_assessment": llm_evaluation,
            "module": "contract_health",
        }

        # Log the action
        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/evaluate-contract",
                "action": "contract_evaluation",
                "timestamp": datetime.utcnow(),
                "status": "success",
            }
        )

        return evaluation
    except HTTPException:
        raise
    except Exception as e:
        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/evaluate-contract",
                "action": "contract_evaluation",
                "timestamp": datetime.utcnow(),
                "status": "error",
                "error": str(e),
            }
        )
        raise HTTPException(status_code=500, detail=format_analysis_error(e, llm_health_check()))


# Backend Services endpoints
@app.post("/pipeline/analyze")
async def pipeline_analysis_endpoint(
    payload: PipelineAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    opportunities = [op.model_dump() for op in payload.opportunities]
    results = analyze_pipeline(opportunities, payload.stage_probabilities)

    await db.logs.insert_one(
        {
            "user": current_user["username"],
            "endpoint": "/pipeline/analyze",
            "action": "pipeline_analysis",
            "timestamp": datetime.utcnow(),
            "status": "success",
            "opportunities_count": len(opportunities),
        }
    )
    return results


@app.get("/logs")
async def get_logs(
    user: Optional[str] = Query(None),
    endpoint: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    filter_dict = {}
    if user:
        filter_dict["user"] = user
    if endpoint:
        filter_dict["endpoint"] = endpoint
    if status:
        filter_dict["status"] = status
    if level:
        filter_dict["level"] = level

    skip = (page - 1) * limit
    logs = await db.logs.find(filter_dict).skip(skip).limit(limit).to_list(limit)
    total = await db.logs.count_documents(filter_dict)

    # Convert ObjectId to string for JSON serialization
    for log in logs:
        log["_id"] = str(log["_id"])

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@app.get("/metrics")
async def get_metrics(current_user: dict = Depends(get_current_user)):
    total_requests = await db.logs.count_documents({})
    successful_requests = await db.logs.count_documents({"status": "success"})
    failed_requests = await db.logs.count_documents({"status": "error"})

    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "success_rate": (
            (successful_requests / total_requests * 100) if total_requests > 0 else 0
        ),
    }




@app.get("/metrics/chat-quality")
async def get_chat_quality_metrics(current_user: dict = Depends(get_current_user)):
    user_filter = {"user": current_user["username"], "action": "contract_chat", "status": "success"}
    total = await db.logs.count_documents(user_filter)
    low_confidence = await db.logs.count_documents({**user_filter, "confidence": {"$lt": 0.35}})
    out_of_scope = await db.logs.count_documents({**user_filter, "intent": "out_of_scope"})
    no_evidence = await db.logs.count_documents({**user_filter, "evidence_count": 0})

    return {
        "total_chat_requests": total,
        "low_confidence_rate": (low_confidence / total * 100) if total else 0,
        "out_of_scope_rate": (out_of_scope / total * 100) if total else 0,
        "no_evidence_rate": (no_evidence / total * 100) if total else 0,
    }

@app.get("/healthz")
async def health_check():
    mongo_ok = "connected"
    try:
        await db_client.admin.command("ping")
    except Exception:
        mongo_ok = "unreachable"
    return {"status": "ok", "mongodb": mongo_ok, "llm": llm_health_check()}


@app.get("/llm/health")
async def llm_health():
    return llm_health_check()


@app.get("/readyz")
async def readiness_check():
    try:
        await db_client.admin.command("ping")
        return {"status": "ready", "timestamp": datetime.utcnow()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


# Clients & Contracts endpoints


# CLIENT CRUD OPERATIONS
@app.post("/clients")
async def create_client(client: Client, current_user: dict = Depends(get_current_user)):
    """Create a new client"""
    client_dict = client.dict()
    client_dict["created_at"] = datetime.utcnow()
    client_dict["created_by"] = current_user["username"]

    result = await db.clients.insert_one(client_dict)
    return {
        "message": "Client created successfully",
        "client_id": str(result.inserted_id),
    }


@app.get("/clients")
async def get_clients(current_user: dict = Depends(get_current_user)):
    """Get all clients for the current user"""
    clients = await db.clients.find({"created_by": current_user["username"]}).to_list(
        100
    )

    # Convert ObjectId to string for JSON serialization
    for client in clients:
        client["_id"] = str(client["_id"])

    return {"clients": clients}


@app.get("/clients/{client_id}")
async def get_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific client by ID"""
    object_id = parse_object_id(client_id, "client ID")
    client = await db.clients.find_one({"_id": object_id})

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check if user has access to this client
    if client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    client["_id"] = str(client["_id"])
    return client


@app.put("/clients/{client_id}")
async def update_client(
    client_id: str, client: Client, current_user: dict = Depends(get_current_user)
):
    """Update a client"""
    object_id = parse_object_id(client_id, "client ID")

    # Check if client exists and user has access
    existing_client = await db.clients.find_one({"_id": object_id})
    if not existing_client:
        raise HTTPException(status_code=404, detail="Client not found")

    if existing_client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    client_dict = client.dict()
    client_dict["updated_at"] = datetime.utcnow()
    client_dict["updated_by"] = current_user["username"]

    result = await db.clients.update_one(
        {"_id": object_id}, {"$set": client_dict}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")

    return {"message": "Client updated successfully"}


@app.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a client"""
    object_id = parse_object_id(client_id, "client ID")

    # Check if client exists and user has access
    existing_client = await db.clients.find_one({"_id": object_id})
    if not existing_client:
        raise HTTPException(status_code=404, detail="Client not found")

    if existing_client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if client has contracts
    contracts = await db.contracts.find({"client_id": client_id}).to_list(1)
    if contracts:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete client with existing contracts. Delete contracts first.",
        )

    result = await db.clients.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")

    return {"message": "Client deleted successfully"}


@app.get("/clients/{client_id}/contracts")
async def get_client_contracts(
    client_id: str, current_user: dict = Depends(get_current_user)
):
    """Get all contracts for a specific client"""
    object_id = parse_object_id(client_id, "client ID")

    # Check if client exists and user has access
    client = await db.clients.find_one({"_id": object_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    contracts = await db.contracts.find({"client_id": client_id}).to_list(100)

    # Convert ObjectId to string for JSON serialization
    for contract in contracts:
        contract["_id"] = str(contract["_id"])

    return {"contracts": contracts}


# CONTRACT CRUD OPERATIONS
@app.post("/contracts")
async def create_contract(
    contract: Contract, current_user: dict = Depends(get_current_user)
):
    """Create a new contract"""
    client_object_id = parse_object_id(contract.client_id, "client ID")

    # Verify that client exists and user has access
    client = await db.clients.find_one({"_id": client_object_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied to client")

    contract_dict = contract.dict()
    contract_dict["created_at"] = datetime.utcnow()
    contract_dict["created_by"] = current_user["username"]

    result = await db.contracts.insert_one(contract_dict)
    return {
        "message": "Contract created successfully",
        "contract_id": str(result.inserted_id),
    }


@app.get("/contracts")
async def get_contracts(current_user: dict = Depends(get_current_user)):
    """Get all contracts for the current user"""
    contracts = await db.contracts.find(
        {"created_by": current_user["username"]}
    ).to_list(100)

    # Convert ObjectId to string for JSON serialization
    for contract in contracts:
        contract["_id"] = str(contract["_id"])

    return {"contracts": contracts}


@app.get("/contracts/{contract_id}")
async def get_contract(
    contract_id: str, current_user: dict = Depends(get_current_user)
):
    """Get a specific contract by ID"""
    object_id = parse_object_id(contract_id, "contract ID")

    contract = await db.contracts.find_one({"_id": object_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Check if user has access to this contract
    if contract.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    contract["_id"] = str(contract["_id"])
    return contract


@app.put("/contracts/{contract_id}")
async def update_contract(
    contract_id: str, contract: Contract, current_user: dict = Depends(get_current_user)
):
    """Update a contract"""
    object_id = parse_object_id(contract_id, "contract ID")
    client_object_id = parse_object_id(contract.client_id, "client ID")

    # Check if contract exists and user has access
    existing_contract = await db.contracts.find_one({"_id": object_id})
    if not existing_contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if existing_contract.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Verify that client exists and user has access
    client = await db.clients.find_one({"_id": client_object_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied to client")

    contract_dict = contract.dict()
    contract_dict["updated_at"] = datetime.utcnow()
    contract_dict["updated_by"] = current_user["username"]

    result = await db.contracts.update_one(
        {"_id": object_id}, {"$set": contract_dict}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contract not found")

    return {"message": "Contract updated successfully"}


@app.delete("/contracts/{contract_id}")
async def delete_contract(
    contract_id: str, current_user: dict = Depends(get_current_user)
):
    """Delete a contract"""
    object_id = parse_object_id(contract_id, "contract ID")

    # Check if contract exists and user has access
    existing_contract = await db.contracts.find_one({"_id": object_id})
    if not existing_contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if existing_contract.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete related contract analyses
    await db.contract_analyses.delete_many({"contract_id": contract_id})

    result = await db.contracts.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contract not found")

    return {"message": "Contract deleted successfully"}


@app.post("/contracts/{contract_id}/init-genai")
async def init_genai_analysis(
    contract_id: str,
    response_language: str = Query("english"),
    current_user: dict = Depends(get_current_user),
):
    object_id = parse_object_id(contract_id, "contract ID")

    contract = await db.contracts.find_one({"_id": object_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if not contract.get("content"):
        raise HTTPException(
            status_code=400, detail="Contract has no content to analyze"
        )

    if not is_genai_configured():
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: Ollama not configured",
        )

    try:
        print("USING VALIDATED CLAUSE EXTRACTION PIPELINE")
        structured_clauses = extract_key_clauses(contract["content"])
        validated_for_health = {k:v.get("extracted_text") for k,v in structured_clauses.get("clauses",{}).items() if isinstance(v,dict) and v.get("status")=="found" and v.get("extracted_text")}
        llm_evaluation = await evaluate_contract(
            validated_for_health or {"summary": contract["content"][:500]},
            response_language=response_language,
        )
        rule_evaluation = evaluate_contract_health_from_clauses(validated_for_health or {"summary": contract["content"][:500]}, response_language=response_language)

        health_evaluation = {
            **llm_evaluation,
            **rule_evaluation,
            "llm_assessment": llm_evaluation,
            "module": "contract_health",
        }
        results = {
            "contract_type": rule_evaluation.get("contract_type"),
            "structured_clauses": structured_clauses,
            "clauses": validated_for_health,
            "health_evaluation": health_evaluation,
            "final_report_summary": {
                "approved": health_evaluation.get("approved"),
                "health_score": health_evaluation.get("health_score"),
                "risk_level": health_evaluation.get("risk_level"),
                "missing_critical_clauses": health_evaluation.get("missing_critical_clauses", []),
                "required_changes": health_evaluation.get("required_changes", []),
            },
        }

        analysis_dict = {
            "contract_id": contract_id,
            "results": results,
            "created_at": datetime.utcnow(),
            "created_by": current_user["username"],
        }

        result = await db.contract_analyses.insert_one(analysis_dict)

        # Update contract status
        await db.contracts.update_one(
            {"_id": object_id},
            {"$set": {"status": "analyzed", "analysis_id": str(result.inserted_id)}},
        )

        return {
            "message": "GenAI analysis completed",
            "analysis_id": str(result.inserted_id),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=format_analysis_error(e, llm_health_check()))


@app.post("/contracts/{contract_id}/chat")
async def chat_with_contract(
    contract_id: str,
    request: ContractChatRequest,
    current_user: dict = Depends(get_current_user),
):
    object_id = parse_object_id(contract_id, "contract ID")

    contract = await db.contracts.find_one({"_id": object_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    message = (request.message or request.question or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Please enter a message for the contract assistant.")

    intent, _ = classify_chat_intent(message)
    context_free_intents = {"small_talk", "app_help", "unsafe_request", "clarification_needed", "general_business_question"}
    if not contract.get("content") and intent not in context_free_intents:
        raise HTTPException(status_code=400, detail="Please analyze this contract before using the assistant.")

    try:
        latest_analysis = await db.contract_analyses.find_one(
            {"contract_id": contract_id},
            sort=[("created_at", -1)],
        )
        analysis_results = (latest_analysis or {}).get("results", {})
        chat_history = [item.dict() for item in request.chat_history]
        structured_answer = build_contract_chat_response(
            message=message,
            contract_text=contract["content"],
            analysis_results=analysis_results,
            benchmark_result=contract.get("benchmark_result"),
            chat_history=chat_history,
            response_language=request.response_language,
            response_mode=request.response_mode,
            debug=request.debug,
        )

        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": f"/contracts/{contract_id}/chat",
                "action": "contract_chat",
                "timestamp": datetime.utcnow(),
                "status": "success",
                "evidence_count": len(structured_answer.get("evidence_snippets", [])),
                "confidence": structured_answer.get("confidence", "Low"),
                "intent": (structured_answer.get("debug") or {}).get("intent", structured_answer.get("answer_type", "unknown")),
                "prompt_preview": message[:200],
                "output_preview": structured_answer.get("answer", "")[:240],
            }
        )

        return structured_answer
    except HTTPException:
        raise
    except Exception as e:
        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": f"/contracts/{contract_id}/chat",
                "action": "contract_chat",
                "timestamp": datetime.utcnow(),
                "status": "error",
                "error": str(e),
            }
        )
        raise HTTPException(status_code=500, detail="The contract assistant hit an unexpected error. Please try again.")




@app.post("/benchmark/compare/{contract_id}")
async def compare_contract_benchmark(contract_id: str, current_user: dict = Depends(get_current_user)):
    ensure_benchmark_enabled()
    object_id = parse_object_id(contract_id, "contract ID")
    contract = await db.contracts.find_one({"_id": object_id, "created_by": current_user["username"]})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    analysis = await db.contract_analyses.find_one({"contract_id": contract_id}, sort=[("created_at", -1)])
    results = (analysis or {}).get("results", {})
    structured = results.get("structured_clauses", {}) if isinstance(results, dict) else {}
    validated_clauses = structured.get("clauses", {}) if isinstance(structured, dict) else {}
    if not validated_clauses:
        raise HTTPException(status_code=400, detail="Please analyze the contract before running benchmark comparison.")

    contract_type = (results.get("contract_type") if isinstance(results, dict) else None) or (results.get("health_evaluation", {}) if isinstance(results, dict) else {}).get("contract_type")
    readiness_review = results.get("health_evaluation", {}) if isinstance(results, dict) else {}
    ai_commentary_fn = generate_benchmark_ai_commentary if llm_health_check().get("reachable") else None
    try:
        benchmark = build_benchmark_comparison(
            contract_id=contract_id,
            validated_clauses=validated_clauses,
            raw_contract_text=contract.get("content", ""),
            contract_type=contract_type,
            jurisdiction=readiness_review.get("jurisdiction") if isinstance(readiness_review, dict) else None,
            readiness_review=readiness_review,
            ai_commentary_fn=ai_commentary_fn,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await db.contracts.update_one(
        {"_id": object_id},
        {"$set": {"benchmark_result": benchmark, "updated_at": datetime.utcnow()}},
    )
    await db.logs.insert_one({
        "user": current_user["username"],
        "endpoint": f"/benchmark/compare/{contract_id}",
        "action": "benchmark_compare",
        "timestamp": datetime.utcnow(),
        "status": "success",
        "alignment_score": benchmark.get("overall_position", {}).get("alignment_score"),
    })
    return benchmark

@app.post("/contracts/{contract_id}/benchmark")
async def run_contract_benchmark(contract_id: str, current_user: dict = Depends(get_current_user)):
    object_id = parse_object_id(contract_id, "contract ID")
    contract = await db.contracts.find_one({"_id": object_id, "created_by": current_user["username"]})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    analysis = await db.contract_analyses.find_one({"contract_id": contract_id}, sort=[("created_at", -1)])
    clauses = ((analysis or {}).get("results") or {}).get("clauses")
    if not isinstance(clauses, dict):
        raise HTTPException(status_code=404, detail="No extracted clauses found. Run analysis first.")
    contract_type = (((analysis or {}).get("results") or {}).get("health_evaluation") or {}).get("contract_type", "general_commercial")
    analysis_results = (analysis or {}).get("results", {})
    structured = analysis_results.get("structured_clauses", {}) if isinstance(analysis_results, dict) else {}
    validated_clauses = structured.get("clauses", {}) if isinstance(structured, dict) else {}
    if validated_clauses:
        result = build_benchmark_comparison(
            contract_id=contract_id,
            validated_clauses=validated_clauses,
            raw_contract_text=contract.get("content", ""),
            contract_type=contract_type,
            readiness_review=analysis_results.get("health_evaluation", {}),
            ai_commentary_fn=generate_benchmark_ai_commentary if llm_health_check().get("reachable") else None,
        )
    else:
        result = run_benchmark(clauses, contract_type)
    await db.contracts.update_one({"_id": object_id}, {"$set": {"benchmark_result": result, "updated_at": datetime.utcnow()}})
    return result


@app.get("/contracts/{contract_id}/benchmark")
async def get_contract_benchmark(contract_id: str, current_user: dict = Depends(get_current_user)):
    object_id = parse_object_id(contract_id, "contract ID")
    contract = await db.contracts.find_one({"_id": object_id, "created_by": current_user["username"]})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    result = contract.get("benchmark_result")
    if not result:
        raise HTTPException(status_code=404, detail="Benchmark has not been run yet.")
    return result


@app.post("/benchmark/ingest")
async def ingest_benchmark_seed(
    payload: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
):
    ensure_benchmark_enabled()

    allow_all = os.getenv("BENCHMARK_ALLOW_ALL_INGEST", "false").lower() == "true"
    if not allow_all and current_user["username"] not in {"admin", "dev"}:
        raise HTTPException(status_code=403, detail="Only admin/dev can ingest benchmark data")

    use_repo_seed = bool(payload.get("use_repo_seed", True))
    clear_first = bool(payload.get("clear_first", False))

    if use_repo_seed:
        result = load_seed_from_repo()
    else:
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise HTTPException(status_code=400, detail="items must be a list")
        result = ingest_seed_dataset(items, clear_first=clear_first)

    await db.logs.insert_one(
        {
            "user": current_user["username"],
            "endpoint": "/benchmark/ingest",
            "action": "benchmark_ingest",
            "timestamp": datetime.utcnow(),
            "status": "success",
            "ingested": result.get("ingested", 0),
            "total": result.get("total", 0),
        }
    )
    return result


@app.post("/benchmark/analyze")
async def benchmark_analyze_endpoint(
    file: UploadFile = File(...),
    contract_type: str = Form(...),
    jurisdiction: str = Form(...),
    industry: Optional[str] = Form(None),
    opt_in_store_user_data: bool = Form(False),
    current_user: dict = Depends(get_current_user),
):
    ensure_benchmark_enabled()

    file_name = file.filename or "uploaded_contract.txt"
    if not file_name.lower().endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(status_code=400, detail="Supported types: .pdf, .docx, .txt")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = run_benchmark_analysis(
            filename=file_name,
            file_bytes=data,
            contract_type=contract_type,
            jurisdiction=jurisdiction,
            industry=industry,
            opt_in_store_user_data=opt_in_store_user_data,
        )

        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/benchmark/analyze",
                "action": "benchmark_analyze",
                "timestamp": datetime.utcnow(),
                "status": "success",
                "contract_type": contract_type,
                "jurisdiction": jurisdiction,
                "industry": industry,
                "overall_score": result.get("overall_score"),
            }
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/benchmark/analyze",
                "action": "benchmark_analyze",
                "timestamp": datetime.utcnow(),
                "status": "error",
                "error": str(exc),
            }
        )
        raise HTTPException(status_code=500, detail=str(exc))


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


@app.get("/stats/summary")
async def stats_summary(current_user: dict = Depends(get_current_user)):
    """Dashboard KPIs for the authenticated user, computed from saved analyses.

    Returns total contracts analysed, last analysis date, average health score,
    a high/medium/low health distribution, the most common missing clause, and a
    breakdown of contracts by detected type.
    """
    analyses = await db.contract_analyses.find(
        {"created_by": current_user["username"]}
    ).sort("created_at", -1).to_list(1000)

    scores: list[float] = []
    distribution = {"high": 0, "medium": 0, "low": 0}
    missing_counter: Dict[str, int] = {}
    type_counter: Dict[str, int] = {}
    last_analysis_date: Optional[str] = None

    for analysis in analyses:
        if last_analysis_date is None and analysis.get("created_at"):
            created = analysis["created_at"]
            last_analysis_date = created.isoformat() if hasattr(created, "isoformat") else str(created)
        results = analysis.get("results", {}) if isinstance(analysis, dict) else {}
        health = results.get("health_evaluation", {}) if isinstance(results, dict) else {}

        score = health.get("health_score")
        bucket = _score_bucket(score)
        if bucket:
            scores.append(float(score))
            distribution[bucket] += 1

        contract_type = health.get("contract_type") or results.get("contract_type")
        if contract_type:
            type_counter[str(contract_type)] = type_counter.get(str(contract_type), 0) + 1

        for clause in health.get("missing_critical_clauses", []) or []:
            missing_counter[str(clause)] = missing_counter.get(str(clause), 0) + 1

    average_health_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    most_common_missing_clause = (
        max(missing_counter, key=missing_counter.get) if missing_counter else ""
    )

    return {
        "total_contracts": len(analyses),
        "last_analysis_date": last_analysis_date,
        "average_health_score": average_health_score,
        "health_distribution": distribution,
        "most_common_missing_clause": most_common_missing_clause,
        "contracts_by_type": type_counter,
    }


@app.post("/auth/reset-password")
async def request_password_reset(payload: PasswordResetRequest):
    """Start a password reset.

    Generates a 32-character token, stores it in the ``password_reset_tokens``
    collection (auto-expiring after 1 hour via a TTL index), and returns it in
    the response. In production this token would be emailed; it is returned here
    for the graduation-project demo. Always responds 200 so the endpoint does not
    reveal whether an email is registered.
    """
    import secrets

    user = await db.users.find_one({"email": payload.email})
    response = {
        "message": "If the email is registered, a reset token has been generated.",
        "note": "Demo mode: the token is returned in this response instead of being emailed.",
    }
    if not user:
        return response

    token = secrets.token_urlsafe(24)[:32]
    await db.password_reset_tokens.insert_one(
        {
            "token": token,
            "username": user["username"],
            "created_at": datetime.utcnow(),
        }
    )
    response["token"] = token
    return response


@app.post("/auth/reset-password/confirm")
async def confirm_password_reset(payload: PasswordResetConfirm):
    """Complete a password reset using a token from /auth/reset-password.

    Verifies the token exists (the TTL index removes expired tokens), hashes the
    new password, updates the user document, and deletes the used token.
    """
    record = await db.password_reset_tokens.find_one({"token": payload.token})
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if len(payload.new_password or "") < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    await db.users.update_one(
        {"username": record["username"]},
        {"$set": {"password": get_password_hash(payload.new_password)}},
    )
    await db.password_reset_tokens.delete_one({"token": payload.token})
    return {"message": "Password updated successfully"}


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


@app.post("/contracts/compare")
async def compare_contracts(
    payload: ContractCompareRequest, current_user: dict = Depends(get_current_user)
):
    """Compare the latest analyses of two of the user's contracts clause by clause.

    Returns each contract's title and health score, a per-clause status/text diff
    with a plain-English difference summary, and an overall recommendation.
    """
    async def _load(contract_id: str):
        object_id = parse_object_id(contract_id, "contract ID")
        contract = await db.contracts.find_one({"_id": object_id})
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        if contract.get("created_by") != current_user["username"]:
            raise HTTPException(status_code=403, detail="Access denied")
        analysis = await db.contract_analyses.find_one(
            {"contract_id": contract_id}, sort=[("created_at", -1)]
        )
        results = (analysis or {}).get("results", {}) if isinstance(analysis, dict) else {}
        return contract, results

    contract_a, results_a = await _load(payload.contract_id_a)
    contract_b, results_b = await _load(payload.contract_id_b)

    def _clauses(results: Dict[str, Any]) -> Dict[str, Any]:
        structured = results.get("structured_clauses", {}) if isinstance(results, dict) else {}
        clauses = structured.get("clauses", {}) if isinstance(structured, dict) else {}
        return clauses if isinstance(clauses, dict) else {}

    clauses_a = _clauses(results_a)
    clauses_b = _clauses(results_b)

    clause_diff = []
    for clause_type in sorted(set(clauses_a) | set(clauses_b)):
        a = clauses_a.get(clause_type, {}) if isinstance(clauses_a.get(clause_type), dict) else {}
        b = clauses_b.get(clause_type, {}) if isinstance(clauses_b.get(clause_type), dict) else {}
        status_a = str(a.get("status", "missing"))
        status_b = str(b.get("status", "missing"))
        text_a = str(a.get("extracted_text") or "")
        text_b = str(b.get("extracted_text") or "")
        clause_diff.append(
            {
                "clause_type": clause_type,
                "status_a": status_a,
                "status_b": status_b,
                "text_a": text_a,
                "text_b": text_b,
                "difference_summary": _clause_difference_summary(
                    clause_type, status_a, text_a, status_b, text_b
                ),
            }
        )

    def _health_score(results: Dict[str, Any]) -> int:
        health = results.get("health_evaluation", {}) if isinstance(results, dict) else {}
        try:
            return int(health.get("health_score") or 0)
        except (TypeError, ValueError):
            return 0

    score_a = _health_score(results_a)
    score_b = _health_score(results_b)
    if score_a == score_b:
        recommendation = "Both contracts score similarly; review the clause differences before deciding."
    else:
        stronger = contract_a if score_a > score_b else contract_b
        recommendation = (
            f"'{stronger.get('title', 'the higher-scoring contract')}' is the stronger contract "
            f"({max(score_a, score_b)} vs {min(score_a, score_b)} health score), but confirm the "
            "clause-level differences match your priorities."
        )

    return {
        "contract_a_title": contract_a.get("title", ""),
        "contract_b_title": contract_b.get("title", ""),
        "clause_diff": clause_diff,
        "health_score_a": score_a,
        "health_score_b": score_b,
        "recommendation": recommendation,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
