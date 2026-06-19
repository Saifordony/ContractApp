"""Self-contained demo/sample data for the no-backend "Try Demo Contract" flow.

Kept free of Streamlit imports so it can be reused by pages and exercised in tests.
"""

from __future__ import annotations

from typing import Any, Dict

DEMO_CLIENT_NAME = "Atlas Engineering LLC"

DEMO_CONTRACT_TEXT = """MASTER SERVICES AGREEMENT

1. Parties
This Agreement is made between Atlas Engineering LLC ("Client") and Nova Software FZ-LLC ("Provider").

2. Payment Terms
The Client shall pay the Provider within 30 days of receiving a valid invoice. Late payments accrue interest at 1.5% per month.

3. Termination
Either party may terminate this Agreement for convenience by giving 30 days written notice. The Client may terminate immediately for material breach.

4. Confidentiality
Each party shall protect the other's confidential information for three (3) years following termination.

5. Limitation of Liability
The Provider's total liability shall not exceed the fees paid in the twelve (12) months preceding the claim.

6. Governing Law
This Agreement is governed by the laws of the Dubai International Financial Centre (DIFC).
"""

DEMO_STRUCTURED_CLAUSES: Dict[str, Any] = {
    "clauses": {
        "parties": {
            "status": "found",
            "confidence": 0.86,
            "extracted_text": "Atlas Engineering LLC (\"Client\") and Nova Software FZ-LLC (\"Provider\").",
            "evidence_snippets": [{"quote": "between Atlas Engineering LLC and Nova Software FZ-LLC", "location": "section:Parties"}],
        },
        "payment_terms": {
            "status": "found",
            "confidence": 0.84,
            "extracted_text": "The Client shall pay the Provider within 30 days of receiving a valid invoice.",
            "evidence_snippets": [{"quote": "pay the Provider within 30 days of receiving a valid invoice", "location": "section:Payment Terms"}],
        },
        "termination": {
            "status": "found",
            "confidence": 0.82,
            "extracted_text": "Either party may terminate this Agreement for convenience by giving 30 days written notice.",
            "evidence_snippets": [{"quote": "terminate this Agreement for convenience by giving 30 days written notice", "location": "section:Termination"}],
        },
        "confidentiality": {
            "status": "found",
            "confidence": 0.80,
            "extracted_text": "Each party shall protect the other's confidential information for three (3) years following termination.",
            "evidence_snippets": [{"quote": "protect the other's confidential information for three (3) years", "location": "section:Confidentiality"}],
        },
        "limitation_of_liability": {
            "status": "found",
            "confidence": 0.78,
            "extracted_text": "The Provider's total liability shall not exceed the fees paid in the twelve (12) months preceding the claim.",
            "evidence_snippets": [{"quote": "total liability shall not exceed the fees paid in the twelve (12) months", "location": "section:Limitation of Liability"}],
        },
        "governing_law": {
            "status": "found",
            "confidence": 0.85,
            "extracted_text": "This Agreement is governed by the laws of the Dubai International Financial Centre (DIFC).",
            "evidence_snippets": [{"quote": "governed by the laws of the Dubai International Financial Centre (DIFC)", "location": "section:Governing Law"}],
        },
        "dispute_resolution": {
            "status": "not_found",
            "confidence": 0.0,
            "extracted_text": None,
            "evidence_snippets": [],
        },
    },
    "conflicts": [],
    "chunk_count": 6,
}

DEMO_ANALYSIS_RESULTS: Dict[str, Any] = {
    "contract_type": "service_agreement",
    "structured_clauses": DEMO_STRUCTURED_CLAUSES,
    "clauses": {
        key: payload["extracted_text"]
        for key, payload in DEMO_STRUCTURED_CLAUSES["clauses"].items()
        if payload.get("status") == "found" and payload.get("extracted_text")
    },
    "health_evaluation": {
        "module": "contract_health",
        "contract_type": "service_agreement",
        "approved": True,
        "health_score": 78,
        "risk_level": "low",
        "executive_summary": "Well-structured service agreement. Most key protections are present; add a dispute-resolution clause before signing.",
        "reasoning": "Detected contract type: service agreement. Health score 78/100 across 5 legal dimensions.",
        "missing_critical_clauses": ["dispute_resolution"],
        "required_changes": ["Add an explicit dispute-resolution / arbitration clause and forum."],
        "issues": ["missing_required:dispute_resolution"],
        "dimensions": [
            {"name": "Risk Exposure", "score": 80, "reason": "Liability is capped to 12 months of fees.", "recommended_action": "Confirm the cap is acceptable.", "supporting_evidence": [{"quote": "total liability shall not exceed the fees paid in the twelve (12) months"}]},
            {"name": "Commercial Clarity", "score": 82, "reason": "Payment timing is clear (30 days).", "recommended_action": "Confirm currency and late-fee mechanics."},
            {"name": "Compliance & Obligations", "score": 76, "reason": "Confidentiality is time-bound.", "recommended_action": "Consider adding audit rights."},
            {"name": "Term & Renewal Risk", "score": 74, "reason": "Termination for convenience is mutual.", "recommended_action": "Clarify renewal terms."},
            {"name": "Dispute & Governing Law", "score": 70, "reason": "Governing law set; dispute forum missing.", "recommended_action": "Add a dispute-resolution clause."},
        ],
        "red_flags": [{"type": "missing_dispute_resolution", "severity": "high", "evidence": []}],
    },
}

# Score-breakdown rows for the score_breakdown_bars() component.
DEMO_SCORE_BREAKDOWN = [
    {"area": "Dispute Resolution", "impact": "Missing forum", "severity": "high", "explanation": "No arbitration or court forum is specified, which can make disputes slow and costly."},
    {"area": "Audit Rights", "impact": "Not present", "severity": "medium", "explanation": "Audit rights would strengthen oversight of the provider's obligations."},
    {"area": "Renewal Terms", "impact": "Unclear", "severity": "low", "explanation": "Renewal mechanics are not spelled out; clarify auto-renewal vs fixed term."},
]
