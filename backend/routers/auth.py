from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from backend.core.security import get_current_user
from backend.database import get_database
from backend.services.auth_service import login_user, register_user, update_user_preferences

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PreferencesRequest(BaseModel):
    language: str = "en"
    theme: str = "light"
    ai_explanation_language: str = "match"
    report_language: str = "match"

@router.post("/register")
async def register(payload: RegisterRequest):
    return {"user": await register_user(get_database(), payload.full_name, payload.email, payload.password)}

@router.post("/login")
async def login(payload: LoginRequest):
    return await login_user(get_database(), payload.email, payload.password)

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user

@router.put("/preferences")
async def preferences(payload: PreferencesRequest, user=Depends(get_current_user)):
    return {"user": await update_user_preferences(get_database(), user["id"], payload.model_dump())}

@router.post("/logout")
async def logout():
    return {"ok": True}
