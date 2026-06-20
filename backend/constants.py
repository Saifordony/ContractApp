"""Canonical domain vocabulary, defined once and reused by extraction, health
scoring, and benchmarking so there is a single source of truth for clause types,
health dimensions, and statuses.
"""
from __future__ import annotations

# Clause taxonomy with bilingual labels. Extend here only — never fork.
CLAUSE_TYPES: list[dict] = [
    {"key": "termination", "label": {"en": "Termination", "ar": "الإنهاء"}},
    {"key": "liability", "label": {"en": "Liability", "ar": "المسؤولية"}},
    {"key": "confidentiality", "label": {"en": "Confidentiality", "ar": "السرية"}},
    {"key": "payment", "label": {"en": "Payment Terms", "ar": "شروط الدفع"}},
    {"key": "renewal", "label": {"en": "Renewal", "ar": "التجديد"}},
    {"key": "intellectual_property", "label": {"en": "Intellectual Property", "ar": "الملكية الفكرية"}},
    {"key": "governing_law", "label": {"en": "Governing Law", "ar": "القانون الحاكم"}},
    {"key": "dispute_resolution", "label": {"en": "Dispute Resolution", "ar": "تسوية النزاعات"}},
    {"key": "indemnification", "label": {"en": "Indemnification", "ar": "التعويض"}},
    {"key": "force_majeure", "label": {"en": "Force Majeure", "ar": "القوة القاهرة"}},
]

CLAUSE_KEYS: list[str] = [c["key"] for c in CLAUSE_TYPES]
CLAUSE_LABELS: dict[str, dict] = {c["key"]: c["label"] for c in CLAUSE_TYPES}

CLAUSE_STATUSES = ["found", "partially_found", "needs_review", "not_found"]

# Health sub-dimensions with bilingual labels.
HEALTH_DIMENSIONS: list[dict] = [
    {"key": "clarity", "label": {"en": "Clarity", "ar": "الوضوح"}},
    {"key": "risk_exposure", "label": {"en": "Risk Exposure", "ar": "التعرض للمخاطر"}},
    {"key": "completeness", "label": {"en": "Completeness", "ar": "الاكتمال"}},
    {"key": "enforceability", "label": {"en": "Enforceability", "ar": "قابلية التنفيذ"}},
]
HEALTH_DIMENSION_KEYS = [d["key"] for d in HEALTH_DIMENSIONS]

# Suggested (open) vocabularies — stored as plain strings, not enforced enums.
CONTRACT_TYPES = [
    "general",
    "nda",
    "service_agreement",
    "employment",
    "lease",
    "sales",
    "license",
    "partnership",
]
REGIONS = ["US", "EU", "UK", "UAE", "KSA", "Other"]


def grade_from_score(score: float) -> str:
    """Map a 0..100 score to a letter grade, used consistently everywhere."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"
