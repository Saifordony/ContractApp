"""Unit tests for password hashing and token helpers."""
from __future__ import annotations

from backend.auth.security import (
    create_access_token,
    decode_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("password123")
    assert hashed != "password123"
    assert verify_password("password123", hashed)
    assert not verify_password("wrong", hashed)


def test_verify_password_handles_bad_hash():
    assert verify_password("anything", "not-a-real-hash") is False


def test_access_token_roundtrip():
    token, expires_in = create_access_token("507f1f77bcf86cd799439011")
    assert expires_in > 0
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "507f1f77bcf86cd799439011"
    assert payload["type"] == "access"


def test_decode_invalid_token_returns_none():
    assert decode_token("garbage.token.value") is None


def test_opaque_token_is_unique_and_hashable():
    a = generate_opaque_token()
    b = generate_opaque_token()
    assert a != b
    assert hash_token(a) == hash_token(a)
    assert hash_token(a) != hash_token(b)
