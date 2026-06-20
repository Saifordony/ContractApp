from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.core.security import get_current_user
from backend.database import get_database
from backend.services.client_service import create_client, list_clients

router = APIRouter(prefix="/clients", tags=["clients"])

class ClientCreate(BaseModel):
    name: str
    industry: str | None = ""
    notes: str | None = ""

@router.get("")
async def clients(user=Depends(get_current_user)):
    return await list_clients(get_database(), user["id"])

@router.post("")
async def create(payload: ClientCreate, user=Depends(get_current_user)):
    return await create_client(get_database(), user["id"], payload.model_dump())
