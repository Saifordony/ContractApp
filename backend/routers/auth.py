"""Registration, login, and password-reset endpoints."""

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status

from backend import main as _main
from backend.models import PasswordResetConfirm, PasswordResetRequest, User, UserLogin

router = APIRouter()


@router.post("/auth/register")
async def register(user: User):
    username = (user.username or "").strip()
    email = (user.email or "").strip().lower()
    password = user.password or ""

    if len(username) < 2:
        raise HTTPException(status_code=422, detail="Name must be at least 2 characters")
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password needs at least 8 characters")

    existing_email = await _main.db.users.find_one({"email": email})
    if existing_email:
        raise HTTPException(status_code=409, detail="This email is already registered")

    existing_username = await _main.db.users.find_one({"username": username})
    if existing_username:
        raise HTTPException(status_code=409, detail="This name is already registered")

    hashed_password = _main.get_password_hash(password)
    user_dict = {
        "username": username,
        "email": email,
        "password": hashed_password,
        "created_at": datetime.utcnow(),
    }

    result = await _main.db.users.insert_one(user_dict)
    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id),
    }


@router.post("/auth/login")
async def login(user: UserLogin):
    identifier = (user.username or "").strip()
    email_identifier = identifier.lower()
    db_user = await _main.db.users.find_one({"email": email_identifier})
    if not db_user:
        db_user = await _main.db.users.find_one({"username": identifier})
    if not db_user or not _main.verify_password(user.password, db_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=_main.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = _main.create_access_token(
        data={"sub": db_user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/reset-password")
async def request_password_reset(payload: PasswordResetRequest):
    """Start a password reset.

    Generates a 32-character token, stores it in the ``password_reset_tokens``
    collection (auto-expiring after 1 hour via a TTL index), and returns it in
    the response. In production this token would be emailed; it is returned here
    for the graduation-project demo. Always responds 200 so the endpoint does not
    reveal whether an email is registered.
    """
    user = await _main.db.users.find_one({"email": payload.email})
    response = {
        "message": "If the email is registered, a reset token has been generated.",
        "note": "Demo mode: the token is returned in this response instead of being emailed.",
    }
    if not user:
        return response

    token = secrets.token_urlsafe(24)[:32]
    await _main.db.password_reset_tokens.insert_one(
        {
            "token": token,
            "username": user["username"],
            "created_at": datetime.utcnow(),
        }
    )
    response["token"] = token
    return response


@router.post("/auth/reset-password/confirm")
async def confirm_password_reset(payload: PasswordResetConfirm):
    """Complete a password reset using a token from /auth/reset-password.

    Verifies the token exists (the TTL index removes expired tokens), hashes the
    new password, updates the user document, and deletes the used token.
    """
    record = await _main.db.password_reset_tokens.find_one({"token": payload.token})
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if len(payload.new_password or "") < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    await _main.db.users.update_one(
        {"username": record["username"]},
        {"$set": {"password": _main.get_password_hash(payload.new_password)}},
    )
    await _main.db.password_reset_tokens.delete_one({"token": payload.token})
    return {"message": "Password updated successfully"}
