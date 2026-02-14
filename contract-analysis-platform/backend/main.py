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


class ContractChatRequest(BaseModel):
    question: str
    response_language: str = "english"


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

        return {"clauses": clauses}
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
        evaluation = await evaluate_contract(
            clauses,
            response_language=response_language,
        )

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
        results = await analyze_and_evaluate_contract(
            contract["content"],
            response_language=response_language,
        )

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
        answer = await contract_chat(
            contract_text=contract["content"],
            question=request.question,
            response_language=request.response_language,
        )

        await db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": f"/contracts/{contract_id}/chat",
                "action": "contract_chat",
                "timestamp": datetime.utcnow(),
                "status": "success",
            }
        )

        return {"answer": answer}
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
