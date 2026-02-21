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
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from backend.gen1 import (
    analyze_contract,
    evaluate_contract,
    extract_text_from_pdf_bytes,
    analyze_and_evaluate_contract,
    contract_chat,
    explain_clauses_for_layman,
)
from backend.services.contract_intelligence import answer_contract_question, extract_key_clauses
from backend.services.contract_health import evaluate_contract_health_from_clauses
from backend.services.pipeline_analysis import analyze_pipeline
from backend.services.benchmark_service import (
    ingest_seed_dataset,
    load_seed_from_repo,
    run_benchmark_analysis,
)

# Load environment variables
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print(
        "WARNING: OPENAI_API_KEY environment variable is not set. GenAI features will be disabled."
    )
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

class ContractChatRequest(BaseModel):
    question: str
    response_language: str = "english"


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
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: OpenAI API key not configured",
        )

    try:
        pdf_bytes = await file.read()
        contract_text = extract_text_from_pdf_bytes(
            pdf_bytes,
            use_ocr=use_ocr,
            response_language=response_language,
        )
        clauses = await analyze_contract(
            contract_text,
            response_language=response_language,
        )
        clause_explanations = await explain_clauses_for_layman(
            clauses,
            response_language=response_language,
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

        return {"clauses": clauses, "clause_explanations": clause_explanations}
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
        raise HTTPException(status_code=500, detail=str(e))




@app.post("/genai/analyze-contract-text")
async def analyze_contract_text_endpoint(
    payload: ContractTextAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: OpenAI API key not configured",
        )

    contract_text = (payload.contract_text or "").strip()
    if not contract_text:
        raise HTTPException(status_code=400, detail="contract_text cannot be empty")

    try:
        clauses = await analyze_contract(
            contract_text,
            response_language=payload.response_language,
        )
        clause_explanations = await explain_clauses_for_layman(
            clauses,
            response_language=payload.response_language,
        )
        structured_clauses = extract_key_clauses(contract_text)

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
            "clauses": clauses,
            "clause_explanations": clause_explanations,
            "structured_clauses": structured_clauses,
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/genai/evaluate-contract")
async def evaluate_contract_endpoint(
    payload: Dict[str, Any], current_user: dict = Depends(get_current_user)
):
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: OpenAI API key not configured",
        )

    try:
        clauses = payload.get("clauses", payload)
        response_language = payload.get("response_language", "english")

        llm_evaluation = await evaluate_contract(
            clauses,
            response_language=response_language,
        )
        rule_evaluation = evaluate_contract_health_from_clauses(clauses)

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
        raise HTTPException(status_code=500, detail=str(e))


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
    return {"status": "healthy", "timestamp": datetime.utcnow()}


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

    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: OpenAI API key not configured",
        )

    try:
        clauses = await analyze_contract(
            contract["content"],
            response_language=response_language,
        )
        clause_explanations = await explain_clauses_for_layman(
            clauses,
            response_language=response_language,
        )
        llm_evaluation = await evaluate_contract(
            clauses,
            response_language=response_language,
        )
        rule_evaluation = evaluate_contract_health_from_clauses(clauses)

        health_evaluation = {
            **llm_evaluation,
            **rule_evaluation,
            "llm_assessment": llm_evaluation,
            "module": "contract_health",
        }
        results = {
            "contract_type": rule_evaluation.get("contract_type"),
            "clauses": clauses,
            "clause_explanations": clause_explanations,
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
        raise HTTPException(status_code=500, detail=str(e))


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

    if not contract.get("content"):
        raise HTTPException(status_code=400, detail="Contract has no content to chat about")

    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: OpenAI API key not configured",
        )

    try:
        latest_analysis = await db.contract_analyses.find_one(
            {"contract_id": contract_id},
            sort=[("created_at", -1)],
        )
        report_context = build_report_context_from_results((latest_analysis or {}).get("results", {}))
        chat_context_text = contract["content"]
        if report_context:
            chat_context_text = f"{chat_context_text}\n\n{report_context}"

        llm_answer = await contract_chat(
            contract_text=chat_context_text,
            question=request.question,
            response_language=request.response_language,
        )
        structured_answer = answer_contract_question(chat_context_text, request.question)

        # Keep chat strictly grounded: never replace structured evidence-based answer with free-form LLM text.
        # Preserve LLM phrasing as optional alternative only when structured grounding succeeded.
        if (
            not structured_answer.get("answer", "").startswith("Not Found")
            and isinstance(llm_answer, str)
            and llm_answer.strip()
        ):
            structured_answer["suggested_natural_answer"] = llm_answer.strip()

        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": f"/contracts/{contract_id}/chat",
                "action": "contract_chat",
                "timestamp": datetime.utcnow(),
                "status": "success",
                "retrieved_chunk_ids": structured_answer.get("retrieved_chunk_ids", []),
                "retrieval_scores": structured_answer.get("retrieval_scores", []),
                "evidence_count": len(structured_answer.get("evidence", [])),
                "confidence": structured_answer.get("confidence", 0.0),
                "intent": structured_answer.get("intent", "unknown"),
                "not_found_count": len(structured_answer.get("not_found", [])),
                "prompt_preview": request.question[:200],
                "output_preview": structured_answer.get("answer", "")[:240],
            }
        )

        return structured_answer
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
        raise HTTPException(status_code=500, detail=str(e))


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
