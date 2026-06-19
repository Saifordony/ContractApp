"""Tests for the dry-run migration planners (pure, no live MongoDB)."""

import asyncio

from bson import ObjectId

from backend.migrations import (
    plan_action_renames,
    plan_clause_consolidation,
    plan_client_id_objectids,
    report_duplicate_accounts,
    run,
    _canonical_clauses,
)


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, _n):
        return list(self._docs)


class _Coll:
    def __init__(self, docs):
        self.docs = docs

    def find(self, _q):
        return _Cursor(self.docs)

    async def update_one(self, query, update):
        for d in self.docs:
            if d.get("_id") == query.get("_id"):
                for key, value in update.get("$set", {}).items():
                    # Interpret Mongo dotted paths as nested dict writes.
                    parts = key.split(".")
                    target = d
                    for part in parts[:-1]:
                        target = target.setdefault(part, {})
                    target[parts[-1]] = value


class _DB:
    def __init__(self, **colls):
        for name, docs in colls.items():
            setattr(self, name, _Coll(docs))


def test_plan_action_renames_counts_only_renamable():
    logs = [
        {"action": "contract_analysis_text"},
        {"action": "contract_analysis_text"},
        {"action": "contract_analysis"},
        {"action": "benchmark_compare"},
    ]
    assert plan_action_renames(logs) == {"contract_analysis_text": 2}


def test_plan_client_id_buckets():
    valid = str(ObjectId())
    contracts = [
        {"_id": 1, "client_id": valid},          # convertible
        {"_id": 2, "client_id": ObjectId()},      # already
        {"_id": 3, "client_id": "not-an-oid"},    # unconvertible
        {"_id": 4, "client_id": None},            # unconvertible
    ]
    buckets = plan_client_id_objectids(contracts)
    assert buckets["convertible"] == [1]
    assert buckets["already"] == [2]
    assert set(buckets["unconvertible"]) == {3, 4}


def test_plan_clause_consolidation_classifies_shapes():
    analyses = [
        {"results": {"clauses": {"a": "x"}, "structured_clauses": {"clauses": {"a": {"status": "found"}}}}},
        {"results": {"structured_clauses": {"clauses": {"a": {"status": "found"}}}}},
        {"results": {"clauses": {"a": "x"}}},
        {"results": {}},
    ]
    report = plan_clause_consolidation(analyses)
    assert report == {"both_shapes": 1, "structured_only": 1, "flat_only": 1, "neither": 1}


def test_canonical_prefers_structured_then_normalises_flat():
    structured = _canonical_clauses({"structured_clauses": {"clauses": {"a": {"status": "found"}}}, "clauses": {"a": "flat"}})
    assert structured == {"a": {"status": "found"}}
    # Flat-only is normalised into the structured shape.
    flat = _canonical_clauses({"clauses": {"payment": "Net 30"}})
    assert flat == {"payment": {"status": "found", "extracted_text": "Net 30"}}
    assert _canonical_clauses({}) is None


def test_report_duplicate_accounts():
    users = [
        {"username": "a", "email": "a@x.com"},
        {"username": "a", "email": "b@x.com"},
        {"username": "c", "email": "a@x.com"},
    ]
    report = report_duplicate_accounts(users)
    assert report["duplicate_usernames"] == ["a"]
    assert report["duplicate_emails"] == ["a@x.com"]


def test_dry_run_changes_nothing():
    valid = str(ObjectId())
    contracts = [{"_id": 1, "client_id": valid}]
    logs = [{"_id": 1, "action": "contract_analysis_text"}]
    db = _DB(users=[], contracts=contracts, contract_analyses=[], logs=logs)
    report = asyncio.run(run(db, apply=False))
    assert report["applied"] is False
    # Untouched.
    assert contracts[0]["client_id"] == valid
    assert logs[0]["action"] == "contract_analysis_text"


def test_apply_migrates_and_preserves_legacy_values():
    valid = str(ObjectId())
    contracts = [{"_id": 1, "client_id": valid}]
    logs = [{"_id": 1, "action": "contract_analysis_text"}]
    analyses = [{"_id": 1, "results": {"clauses": {"payment": "Net 30"}}}]
    db = _DB(users=[], contracts=contracts, contract_analyses=analyses, logs=logs)
    report = asyncio.run(run(db, apply=True))
    assert report["applied"] is True
    # client_id converted, original preserved.
    assert isinstance(contracts[0]["client_id"], ObjectId)
    assert contracts[0]["_legacy_client_id"] == valid
    # action renamed, original preserved.
    assert logs[0]["action"] == "contract_analysis"
    assert logs[0]["_legacy_action"] == "contract_analysis_text"
    # flat clauses normalised into the structured shape.
    assert analyses[0]["results"]["structured_clauses"]["clauses"] == {
        "payment": {"status": "found", "extracted_text": "Net 30"}
    }
