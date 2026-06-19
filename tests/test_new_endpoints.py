"""Integration tests for the new dashboard / auth / comparison endpoints.

A small in-memory async fake stands in for Motor so the routes can be exercised
without a live MongoDB.
"""

import datetime
import importlib
import sys
import types

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient


def _match(doc, query):
    for key, value in (query or {}).items():
        if doc.get(key) != value:
            return False
    return True


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key, direction=-1):
        self._docs.sort(key=lambda d: (d.get(key) is None, d.get(key)), reverse=(direction == -1))
        return self

    async def to_list(self, n):
        return self._docs[:n]


class _Collection:
    def __init__(self):
        self.docs = []

    def find(self, query=None):
        return _Cursor([d for d in self.docs if _match(d, query or {})])

    async def find_one(self, query=None, sort=None):
        matches = [d for d in self.docs if _match(d, query or {})]
        if sort:
            key, direction = sort[0]
            matches.sort(key=lambda d: (d.get(key) is None, d.get(key)), reverse=(direction == -1))
        return matches[0] if matches else None

    async def insert_one(self, doc):
        doc.setdefault("_id", ObjectId())
        self.docs.append(doc)
        return types.SimpleNamespace(inserted_id=doc["_id"])

    async def update_one(self, query, update):
        for d in self.docs:
            if _match(d, query):
                d.update(update.get("$set", {}))
                return types.SimpleNamespace(matched_count=1, modified_count=1)
        return types.SimpleNamespace(matched_count=0, modified_count=0)

    async def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if _match(d, query):
                del self.docs[i]
                return types.SimpleNamespace(deleted_count=1)
        return types.SimpleNamespace(deleted_count=0)

    async def create_index(self, *args, **kwargs):
        return "idx"


class _FakeDB:
    def __init__(self):
        self._collections = {}

    def __getattr__(self, name):
        # Lazily create collections on attribute access (db.users, db.contracts...).
        collections = self.__dict__.setdefault("_collections", {})
        if name not in collections:
            collections[name] = _Collection()
        return collections[name]


@pytest.fixture
def app_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "endpoint-secret")

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
    fake_gen1.extract_text_from_pdf_bytes = lambda *a, **k: "sample text"
    fake_gen1.extract_text_from_upload_bytes = lambda *a, **k: "sample text"
    fake_gen1.llm_model = None

    sys.modules["backend.gen1"] = fake_gen1
    sys.modules.pop("backend.main", None)

    module = importlib.import_module("backend.main")
    module.db = _FakeDB()

    async def _fake_current_user():
        return {"username": "alice"}

    module.app.dependency_overrides[module.get_current_user] = _fake_current_user
    return module


def _seed_analysis(module, contract_id, score, contract_type, missing, created_at):
    module.db.contract_analyses.docs.append(
        {
            "contract_id": contract_id,
            "created_by": "alice",
            "created_at": created_at,
            "results": {
                "contract_type": contract_type,
                "health_evaluation": {
                    "health_score": score,
                    "contract_type": contract_type,
                    "missing_critical_clauses": missing,
                },
                "structured_clauses": {
                    "clauses": {
                        "termination": {"status": "found", "extracted_text": "30 days notice."},
                        "governing_law": {"status": "not_found", "extracted_text": None},
                    }
                },
            },
        }
    )


def test_stats_summary_aggregates_user_analyses(app_module):
    module = app_module
    base = datetime.datetime(2026, 1, 1)
    _seed_analysis(module, "c1", 82, "employment", ["governing_law"], base)
    _seed_analysis(module, "c2", 64, "nda", ["governing_law", "liability"], base + datetime.timedelta(days=1))
    _seed_analysis(module, "c3", 40, "employment", ["governing_law", "liability"], base + datetime.timedelta(days=2))

    client = TestClient(module.app)
    resp = client.get("/stats/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_contracts"] == 3
    assert data["average_health_score"] == pytest.approx((82 + 64 + 40) / 3, abs=0.1)
    assert data["health_distribution"] == {"high": 1, "medium": 1, "low": 1}
    assert data["most_common_missing_clause"] == "governing_law"
    assert data["contracts_by_type"] == {"employment": 2, "nda": 1}
    # Most recent analysis date is surfaced.
    assert data["last_analysis_date"].startswith("2026-01-03")


def test_stats_summary_empty_is_graceful(app_module):
    client = TestClient(app_module.app)
    data = client.get("/stats/summary").json()
    assert data["total_contracts"] == 0
    assert data["average_health_score"] == 0.0
    assert data["most_common_missing_clause"] == ""


def test_password_reset_flow(app_module):
    module = app_module
    module.db.users.docs.append({"username": "alice", "email": "alice@example.com", "password": "old"})
    client = TestClient(module.app)

    # Request a token.
    resp = client.post("/auth/reset-password", json={"email": "alice@example.com"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    assert len(token) == 32

    # Confirm with the token.
    confirm = client.post(
        "/auth/reset-password/confirm", json={"token": token, "new_password": "brand-new-pass"}
    )
    assert confirm.status_code == 200
    user = module.db.users.docs[0]
    assert user["password"] != "old"  # hashed + updated
    assert module.verify_password("brand-new-pass", user["password"])
    # Token is single-use.
    assert module.db.password_reset_tokens.docs == []


def test_password_reset_unknown_email_does_not_leak(app_module):
    client = TestClient(app_module.app)
    resp = client.post("/auth/reset-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert "token" not in resp.json()


def test_password_reset_confirm_rejects_bad_token(app_module):
    client = TestClient(app_module.app)
    resp = client.post(
        "/auth/reset-password/confirm", json={"token": "does-not-exist", "new_password": "whatever12"}
    )
    assert resp.status_code == 400


def test_contracts_compare_builds_clause_diff(app_module):
    module = app_module
    id_a = ObjectId()
    id_b = ObjectId()
    module.db.contracts.docs.append({"_id": id_a, "title": "Contract A", "created_by": "alice"})
    module.db.contracts.docs.append({"_id": id_b, "title": "Contract B", "created_by": "alice"})
    now = datetime.datetime(2026, 2, 1)
    _seed_analysis(module, str(id_a), 80, "employment", [], now)
    # Contract B lacks termination wording.
    module.db.contract_analyses.docs.append(
        {
            "contract_id": str(id_b),
            "created_by": "alice",
            "created_at": now,
            "results": {
                "health_evaluation": {"health_score": 55},
                "structured_clauses": {
                    "clauses": {
                        "termination": {"status": "not_found", "extracted_text": None},
                        "governing_law": {"status": "not_found", "extracted_text": None},
                    }
                },
            },
        }
    )

    client = TestClient(module.app)
    resp = client.post(
        "/contracts/compare", json={"contract_id_a": str(id_a), "contract_id_b": str(id_b)}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["contract_a_title"] == "Contract A"
    assert data["health_score_a"] == 80
    assert data["health_score_b"] == 55
    assert "Contract A" in data["recommendation"]
    termination = next(d for d in data["clause_diff"] if d["clause_type"] == "termination")
    assert termination["status_a"] == "found"
    assert termination["status_b"] == "not_found"
    assert "Contract A defines termination" in termination["difference_summary"]
