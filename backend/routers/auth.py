from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from backend.core.security import get_current_user
from backend.database import get_database
from backend.services.auth_service import login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
async def register(payload: RegisterRequest):
    return {"user": await register_user(get_database(), payload.full_name, payload.email, payload.password)}

@router.post("/login")
async def login(payload: LoginRequest):
    return await login_user(get_database(), payload.email, payload.password)

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user

@router.post("/logout")
async def logout():
    return {"ok": True}
