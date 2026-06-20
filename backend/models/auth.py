"""Auth domain models: registration, login, tokens, preferences."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.models.common import Email, OutBase

Theme = Literal["light", "dark"]
Language = Literal["en", "ar"]


class Preferences(BaseModel):
    theme: Theme = "light"
    language: Language = "en"


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    email: Email
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=120)


class LoginIn(BaseModel):
    username: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str


class PreferencesIn(BaseModel):
    theme: Optional[Theme] = None
    language: Optional[Language] = None


class PasswordResetRequestIn(BaseModel):
    email: Email


class PasswordResetConfirmIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(OutBase):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    preferences: Preferences = Preferences()
    created_at: datetime


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    user: UserOut
    tokens: Tokens


class PasswordResetRequestOut(BaseModel):
    detail: str
    # Present only when the server is configured to expose reset tokens (dev/no mail).
    reset_token: Optional[str] = None
