"""Seed data for the single benchmark knowledge base (``benchmark_standards``).

Each standard describes the typical clauses expected for a contract type/region,
their importance, and a short description of typical terms. The benchmark engine
compares an analyzed contract's extracted clauses against these expectations.
"""
from __future__ import annotations

_COMMON_CORE = [
    {"key": "termination", "importance": "high",
     "typical_terms": "Either party may terminate on 30 days' written notice; immediate termination for material breach.",
     "description": "Clear notice periods and grounds for termination."},
    {"key": "liability", "importance": "high",
     "typical_terms": "Liability capped at fees paid in the prior 12 months; consequential damages excluded.",
     "description": "A defined liability cap and exclusion of indirect damages."},
    {"key": "confidentiality", "importance": "high",
     "typical_terms": "Mutual confidentiality with 2-5 year survival after termination.",
     "description": "Protection of confidential information with a survival period."},
    {"key": "governing_law", "importance": "medium",
     "typical_terms": "Governed by the laws of the stated jurisdiction.",
     "description": "An explicit governing-law jurisdiction."},
    {"key": "dispute_resolution", "importance": "medium",
     "typical_terms": "Disputes resolved by arbitration or the courts of the governing jurisdiction.",
     "description": "A defined forum and mechanism for disputes."},
]


def _standard(contract_type: str, region: str, clauses: list[dict], language: str = "en") -> dict:
    return {"contract_type": contract_type, "region": region, "language": language, "clauses": clauses}


BENCHMARK_STANDARDS: list[dict] = [
    _standard("general", "US", _COMMON_CORE + [
        {"key": "payment", "importance": "high",
         "typical_terms": "Net-30 payment terms; late fees on overdue amounts.",
         "description": "Defined payment schedule and consequences for late payment."},
        {"key": "force_majeure", "importance": "medium",
         "typical_terms": "Excuses performance for events beyond reasonable control.",
         "description": "A force-majeure clause covering uncontrollable events."},
    ]),
    _standard("nda", "US", [
        {"key": "confidentiality", "importance": "high",
         "typical_terms": "Defines confidential information broadly; obligations survive 3-5 years.",
         "description": "Core confidentiality obligations and survival."},
        {"key": "intellectual_property", "importance": "high",
         "typical_terms": "No license to IP is granted by disclosure.",
         "description": "Clarifies that disclosure grants no IP rights."},
        {"key": "termination", "importance": "medium",
         "typical_terms": "Agreement terminates on notice; confidentiality survives.",
         "description": "Termination with surviving confidentiality."},
        {"key": "governing_law", "importance": "medium",
         "typical_terms": "Governed by the laws of the stated jurisdiction.",
         "description": "An explicit governing-law jurisdiction."},
        {"key": "dispute_resolution", "importance": "low",
         "typical_terms": "Injunctive relief available for breach.",
         "description": "Remedies for breach including injunctive relief."},
    ]),
    _standard("service_agreement", "US", _COMMON_CORE + [
        {"key": "payment", "importance": "high",
         "typical_terms": "Milestone or recurring fees; Net-30; expenses pre-approved.",
         "description": "Detailed fee and payment structure."},
        {"key": "intellectual_property", "importance": "high",
         "typical_terms": "Work product assigned to the client on payment.",
         "description": "Ownership of deliverables and work product."},
        {"key": "indemnification", "importance": "high",
         "typical_terms": "Each party indemnifies for third-party claims arising from its breach.",
         "description": "Mutual indemnification for third-party claims."},
        {"key": "renewal", "importance": "medium",
         "typical_terms": "Auto-renews for successive 12-month terms unless cancelled.",
         "description": "Renewal mechanics and cancellation window."},
    ]),
    _standard("employment", "US", [
        {"key": "payment", "importance": "high",
         "typical_terms": "Salary, pay frequency, and benefits clearly stated.",
         "description": "Compensation and benefits."},
        {"key": "termination", "importance": "high",
         "typical_terms": "At-will or notice-based termination with cause definitions.",
         "description": "Termination terms and notice."},
        {"key": "confidentiality", "importance": "high",
         "typical_terms": "Employee confidentiality and non-disclosure obligations.",
         "description": "Confidentiality obligations of the employee."},
        {"key": "intellectual_property", "importance": "high",
         "typical_terms": "Inventions and work product assigned to the employer.",
         "description": "Assignment of inventions."},
        {"key": "governing_law", "importance": "medium",
         "typical_terms": "Governed by the state of employment.",
         "description": "Governing law for the employment relationship."},
    ]),
    _standard("general", "UAE", _COMMON_CORE + [
        {"key": "payment", "importance": "high",
         "typical_terms": "Payment terms in AED; late payment interest per UAE Civil Code.",
         "description": "Payment schedule consistent with UAE practice."},
        {"key": "force_majeure", "importance": "medium",
         "typical_terms": "Force majeure consistent with UAE Civil Code Article 273.",
         "description": "Force-majeure provision aligned to local law."},
    ], language="ar"),
]
