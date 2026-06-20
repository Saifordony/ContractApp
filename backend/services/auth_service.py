from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from fastapi import HTTPException, status
from backend.core.security import create_access_token, hash_password, verify_password


def serialize_user(user):
    return {
        "id": str(user.get("_id", user.get("id"))),
        "full_name": user.get("full_name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "user"),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }

async def register_user(db, full_name: str, email: str, password: str):
    email = email.strip().lower()
    full_name = full_name.strip()
    if len(full_name) < 2:
        raise HTTPException(422, "Full name must be at least 2 characters.")
    if "@" not in email or "." not in email:
        raise HTTPException(422, "Enter a valid email address.")
    if len(password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters.")
    now = datetime.now(timezone.utc)
    doc = {"full_name": full_name, "email": email, "hashed_password": hash_password(password), "role": "user", "created_at": now, "updated_at": now, "is_active": True}
    try:
        result = await db.users.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "This email is already registered.") from exc
    doc["_id"] = result.inserted_id
    return serialize_user(doc)

async def login_user(db, email: str, password: str):
    user = await db.users.find_one({"email": email.strip().lower(), "is_active": True})
    if not user or not verify_password(password, user.get("hashed_password", "")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    safe_user = serialize_user(user)
    return {"access_token": create_access_token(safe_user["id"]), "token_type": "bearer", "user": safe_user}
