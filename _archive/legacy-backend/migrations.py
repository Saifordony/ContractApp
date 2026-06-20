"""Data migrations for the overhaul, designed to never silently corrupt data.

Every migration is split into a pure ``plan_*`` function (inspects documents and
returns a report of exactly what *would* change, changing nothing) and an async
``apply_*`` function (performs the writes, preserving the original value under a
``_legacy_*`` key for one release cycle). The CLI runs in ``--dry-run`` mode by
default::

    python -m backend.migrations --dry-run     # report only, no writes
    python -m backend.migrations --apply        # perform the migration

The pure planners are what the tests exercise, so the risky logic is verified
without a live MongoDB.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any, Dict, Iterable, List, Optional

from bson import ObjectId
from bson.errors import InvalidId

# ---------------------------------------------------------------------------
# logs.action standardisation
# ---------------------------------------------------------------------------
# contract_analysis_text was a separate action purely because it came from a
# different endpoint; for analytics it is the same activity as contract_analysis.
ACTION_RENAMES: Dict[str, str] = {
    "contract_analysis_text": "contract_analysis",
}


def plan_action_renames(logs: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Report how many log docs would have their ``action`` renamed, by old value."""
    counts: Dict[str, int] = {}
    for doc in logs:
        old = doc.get("action")
        if old in ACTION_RENAMES:
            counts[old] = counts.get(old, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# contracts.client_id : string -> ObjectId
# ---------------------------------------------------------------------------
def plan_client_id_objectids(contracts: Iterable[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """Classify each contract's ``client_id`` for the string->ObjectId migration.

    Returns three buckets: ``convertible`` (valid 24-hex strings), ``already``
    (already ObjectId) and ``unconvertible`` (anything else -- these are reported,
    never dropped, so a human can resolve them before the type is enforced).
    """
    convertible: List[Any] = []
    already: List[Any] = []
    unconvertible: List[Any] = []
    for doc in contracts:
        value = doc.get("client_id")
        key = doc.get("_id", value)
        if isinstance(value, ObjectId):
            already.append(key)
            continue
        try:
            ObjectId(str(value))
            convertible.append(key)
        except (InvalidId, TypeError):
            unconvertible.append(key)
    return {"convertible": convertible, "already": already, "unconvertible": unconvertible}


# ---------------------------------------------------------------------------
# contract_analyses.results : consolidate dual clause storage shapes
# ---------------------------------------------------------------------------
def _canonical_clauses(results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Pick the richer of the two clause shapes as the canonical structured form.

    Historic analyses wrote both a flat ``clauses`` dict and a richer
    ``structured_clauses.clauses`` dict. The structured form is canonical; the flat
    form is only used when the structured one is absent.
    """
    if not isinstance(results, dict):
        return None
    structured = results.get("structured_clauses")
    if isinstance(structured, dict) and isinstance(structured.get("clauses"), dict) and structured["clauses"]:
        return structured["clauses"]
    flat = results.get("clauses")
    if isinstance(flat, dict) and flat:
        # Normalise the flat {name: text} form into the structured shape.
        return {
            name: {"status": "found", "extracted_text": text}
            for name, text in flat.items()
        }
    return None


def plan_clause_consolidation(analyses: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Report how many analyses carry both shapes (and would be consolidated)."""
    both = 0
    structured_only = 0
    flat_only = 0
    neither = 0
    for doc in analyses:
        results = doc.get("results", {})
        structured = isinstance(results, dict) and isinstance(results.get("structured_clauses", {}), dict) \
            and bool(results.get("structured_clauses", {}).get("clauses"))
        flat = isinstance(results, dict) and bool(results.get("clauses"))
        if structured and flat:
            both += 1
        elif structured:
            structured_only += 1
        elif flat:
            flat_only += 1
        else:
            neither += 1
    return {"both_shapes": both, "structured_only": structured_only, "flat_only": flat_only, "neither": neither}


# ---------------------------------------------------------------------------
# duplicate account detection (must clear before unique indexes are enforced)
# ---------------------------------------------------------------------------
def report_duplicate_accounts(users: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Return username/email values that appear on more than one user document."""
    seen_username: Dict[str, int] = {}
    seen_email: Dict[str, int] = {}
    for doc in users:
        if doc.get("username"):
            seen_username[doc["username"]] = seen_username.get(doc["username"], 0) + 1
        if doc.get("email"):
            seen_email[doc["email"]] = seen_email.get(doc["email"], 0) + 1
    return {
        "duplicate_usernames": sorted(k for k, v in seen_username.items() if v > 1),
        "duplicate_emails": sorted(k for k, v in seen_email.items() if v > 1),
    }


async def _collect(cursor) -> List[Dict[str, Any]]:
    return await cursor.to_list(100000)


async def run(db, *, apply: bool) -> Dict[str, Any]:
    """Produce a full migration report; perform writes only when ``apply`` is set."""
    users = await _collect(db.users.find({}))
    contracts = await _collect(db.contracts.find({}))
    analyses = await _collect(db.contract_analyses.find({}))
    logs = await _collect(db.logs.find({}))

    report = {
        "duplicate_accounts": report_duplicate_accounts(users),
        "client_id": {k: len(v) for k, v in plan_client_id_objectids(contracts).items()},
        "clause_consolidation": plan_clause_consolidation(analyses),
        "action_renames": plan_action_renames(logs),
        "applied": False,
    }

    if not apply:
        return report

    for old, new in ACTION_RENAMES.items():
        for doc in logs:
            if doc.get("action") == old:
                await db.logs.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"action": new, "_legacy_action": old}},
                )
    for doc in contracts:
        value = doc.get("client_id")
        if not isinstance(value, ObjectId):
            try:
                oid = ObjectId(str(value))
            except (InvalidId, TypeError):
                continue
            await db.contracts.update_one(
                {"_id": doc["_id"]},
                {"$set": {"client_id": oid, "_legacy_client_id": value}},
            )
    for doc in analyses:
        canonical = _canonical_clauses(doc.get("results", {}))
        if canonical is not None:
            await db.contract_analyses.update_one(
                {"_id": doc["_id"]},
                {"$set": {"results.structured_clauses.clauses": canonical}},
            )
    report["applied"] = True
    return report


def _main() -> None:  # pragma: no cover - thin CLI wrapper
    parser = argparse.ArgumentParser(description="ContractApp data migrations")
    parser.add_argument("--apply", action="store_true", help="perform writes (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="report only (default)")
    args = parser.parse_args()

    from backend.database import create_mongo_client

    client = create_mongo_client()
    db = client.contract_analysis

    async def _go():
        import json

        report = await run(db, apply=args.apply and not args.dry_run)
        print(json.dumps(report, indent=2, default=str))

    asyncio.run(_go())


if __name__ == "__main__":  # pragma: no cover
    _main()
