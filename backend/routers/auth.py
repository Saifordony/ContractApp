"""Authentication router: register, login (rate-limited), refresh-token rotation,
real logout (revocation), current user, server-side preferences, password reset.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.auth.rate_limit import clear_attempts, count_recent_attempts, record_attempt
from backend.auth.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from backend.config import get_settings
from backend.database import get_database
from backend.dependencies import get_current_user
from backend.errors import ApiError
from backend.models.auth import (
    AuthResponse,
    LoginIn,
    LogoutIn,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    PasswordResetRequestOut,
    PreferencesIn,
    RefreshIn,
    RegisterIn,
    Tokens,
    UserOut,
)
from backend.models.common import utcnow
from backend.services.audit import record_log

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_tokens(db: AsyncIOMotorDatabase, user: dict) -> Tokens:
    settings = get_settings()
    access_token, expires_in = create_access_token(str(user["_id"]))
    raw_refresh = generate_opaque_token()
    await db.refresh_tokens.insert_one({
        "user_id": user["_id"],
        "token_hash": hash_token(raw_refresh),
        "expires_at": utcnow() + timedelta(days=settings.refresh_token_expire_days),
        "revoked": False,
        "created_at": utcnow(),
    })
    return Tokens(access_token=access_token, refresh_token=raw_refresh, expires_in=expires_in)


def _auth_response(db: AsyncIOMotorDatabase, user: dict, tokens: Tokens) -> AuthResponse:
    return AuthResponse(user=UserOut.from_doc(user), tokens=tokens)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, db: AsyncIOMotorDatabase = Depends(get_database)) -> AuthResponse:
    if await db.users.find_one({"username": payload.username}):
        raise ApiError(409, "Username already taken", "username_taken")
    if await db.users.find_one({"email": payload.email}):
        raise ApiError(409, "Email already registered", "email_taken")

    now = utcnow()
    doc = {
        "username": payload.username,
        "email": payload.email,
        "hashed_password": hash_password(payload.password),
        "full_name": payload.full_name,
        "preferences": {"theme": "light", "language": "en"},
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = await db.users.insert_one(doc)
    except Exception:
        # Unique index is the backstop against a register/register race.
        raise ApiError(409, "Username or email already registered", "duplicate_account")
    doc["_id"] = result.inserted_id

    tokens = await _issue_tokens(db, doc)
    await record_log(db, "user_register", user_id=doc["_id"], resource_type="user", resource_id=doc["_id"])
    return _auth_response(db, doc, tokens)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginIn, request: Request, db: AsyncIOMotorDatabase = Depends(get_database)) -> AuthResponse:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{payload.username.lower()}"

    if await count_recent_attempts(db, key, settings.login_rate_limit_window_seconds) >= settings.login_rate_limit_max:
        raise ApiError(429, "Too many login attempts. Please wait and try again.", "rate_limited")

    user = await db.users.find_one({"username": payload.username})
    if user is None or not verify_password(payload.password, user["hashed_password"]):
        await record_attempt(db, key)
        raise ApiError(401, "Invalid username or password", "invalid_credentials")

    await clear_attempts(db, key)
    tokens = await _issue_tokens(db, user)
    await record_log(db, "user_login", user_id=user["_id"], resource_type="user", resource_id=user["_id"])
    return _auth_response(db, user, tokens)


@router.post("/refresh", response_model=Tokens)
async def refresh(payload: RefreshIn, db: AsyncIOMotorDatabase = Depends(get_database)) -> Tokens:
    token_doc = await db.refresh_tokens.find_one({"token_hash": hash_token(payload.refresh_token)})
    if token_doc is None or token_doc.get("revoked") or token_doc["expires_at"] <= utcnow():
        raise ApiError(401, "Invalid or expired refresh token", "invalid_refresh")

    user = await db.users.find_one({"_id": token_doc["user_id"]})
    if user is None:
        raise ApiError(401, "User no longer exists", "unauthorized")

    # Rotate: revoke the presented token, issue a fresh pair.
    await db.refresh_tokens.update_one({"_id": token_doc["_id"]}, {"$set": {"revoked": True}})
    return await _issue_tokens(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutIn, db: AsyncIOMotorDatabase = Depends(get_database)) -> Response:
    await db.refresh_tokens.update_one(
        {"token_hash": hash_token(payload.refresh_token)}, {"$set": {"revoked": True}}
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)) -> UserOut:
    return UserOut.from_doc(current_user)


@router.patch("/me/preferences", response_model=UserOut)
async def update_preferences(
    payload: PreferencesIn,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> UserOut:
    updates = payload.model_dump(exclude_none=True)
    if updates:
        prefs = {**current_user.get("preferences", {}), **updates}
        await db.users.update_one(
            {"_id": current_user["_id"]},
            {"$set": {"preferences": prefs, "updated_at": utcnow()}},
        )
        current_user["preferences"] = prefs
    return UserOut.from_doc(current_user)


@router.post("/password-reset/request", response_model=PasswordResetRequestOut, status_code=status.HTTP_202_ACCEPTED)
async def password_reset_request(
    payload: PasswordResetRequestIn, db: AsyncIOMotorDatabase = Depends(get_database)
) -> PasswordResetRequestOut:
    settings = get_settings()
    generic = "If that email is registered, a reset link has been sent."
    user = await db.users.find_one({"email": payload.email})
    if user is None:
        # Do not reveal whether the email exists.
        return PasswordResetRequestOut(detail=generic)

    raw_token = generate_opaque_token()
    await db.password_reset_tokens.insert_one({
        "user_id": user["_id"],
        "token_hash": hash_token(raw_token),
        "expires_at": utcnow() + timedelta(minutes=settings.password_reset_expire_minutes),
        "used": False,
        "created_at": utcnow(),
    })
    await record_log(db, "user_password_reset_request", user_id=user["_id"], resource_type="user")
    # In dev/no-mail mode the token is returned so the UI can complete the flow.
    return PasswordResetRequestOut(
        detail=generic, reset_token=raw_token if settings.expose_reset_token else None
    )


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def password_reset_confirm(
    payload: PasswordResetConfirmIn, db: AsyncIOMotorDatabase = Depends(get_database)
) -> Response:
    token_doc = await db.password_reset_tokens.find_one({"token_hash": hash_token(payload.token)})
    if token_doc is None or token_doc.get("used") or token_doc["expires_at"] <= utcnow():
        raise ApiError(400, "Invalid or expired reset token", "invalid_reset")

    await db.users.update_one(
        {"_id": token_doc["user_id"]},
        {"$set": {"hashed_password": hash_password(payload.new_password), "updated_at": utcnow()}},
    )
    await db.password_reset_tokens.update_one({"_id": token_doc["_id"]}, {"$set": {"used": True}})
    # Revoke all refresh tokens — a password reset invalidates existing sessions.
    await db.refresh_tokens.update_many({"user_id": token_doc["user_id"]}, {"$set": {"revoked": True}})
    await record_log(db, "user_password_reset_confirm", user_id=token_doc["user_id"], resource_type="user")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
