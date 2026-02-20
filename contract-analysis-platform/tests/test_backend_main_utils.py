import importlib
import sys
import types

import pytest
from fastapi import HTTPException
from jose import jwt


@pytest.fixture
def backend_main(monkeypatch):
    """Import backend.main with a stubbed backend.gen1 to keep unit tests isolated."""
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")

    fake_gen1 = types.ModuleType("backend.gen1")

    async def _async_dict(*args, **kwargs):
        return {}

    async def _async_str(*args, **kwargs):
        return "ok"

    fake_gen1.analyze_contract = _async_dict
    fake_gen1.evaluate_contract = _async_dict
    fake_gen1.analyze_and_evaluate_contract = _async_dict
    fake_gen1.explain_clauses_for_layman = _async_dict
    fake_gen1.contract_chat = _async_str
    fake_gen1.extract_text_from_pdf_bytes = lambda *args, **kwargs: "sample text"

    sys.modules["backend.gen1"] = fake_gen1
    sys.modules.pop("backend.main", None)

    return importlib.import_module("backend.main")


def test_password_hash_roundtrip(backend_main):
    password = "P@ssword-123"
    hashed = backend_main.get_password_hash(password)

    assert hashed != password
    assert backend_main.verify_password(password, hashed)
    assert not backend_main.verify_password("wrong-password", hashed)


def test_create_access_token_has_subject(backend_main):
    token = backend_main.create_access_token({"sub": "qa-user"})
    decoded = jwt.decode(
        token,
        backend_main.SECRET_KEY,
        algorithms=[backend_main.ALGORITHM],
    )

    assert decoded["sub"] == "qa-user"
    assert "exp" in decoded


def test_parse_object_id_valid_and_invalid(backend_main):
    oid = backend_main.parse_object_id("507f1f77bcf86cd799439011", "contract ID")
    assert str(oid) == "507f1f77bcf86cd799439011"

    with pytest.raises(HTTPException) as exc:
        backend_main.parse_object_id("invalid-id", "contract ID")

    assert exc.value.status_code == 400
    assert "Invalid contract ID" in exc.value.detail
