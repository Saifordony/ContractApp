"""Stable user-facing AI output schemas for contract intelligence services."""
from __future__ import annotations

from typing import Any
try:
    from pydantic import BaseModel, Field
except Exception:  # minimal offline test environments may not have pydantic installed
    def Field(default_factory=None, default=None, **_: Any):
        return default_factory() if default_factory is not None else default
    class BaseModel:
        def __init__(self, **data: Any):
            for key, value in data.items():
                setattr(self, key, value)
        def model_dump(self) -> dict[str, Any]:
            return dict(self.__dict__)


class EvidenceQuote(BaseModel):
    text: str = ""
    source: str = "extracted_contract_text"
    section_title: str | None = None
    section_reference: str | None = None
    chunk_id: str | None = None
    score: float = 0.0
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    start_char: int | None = None
    end_char: int | None = None
    page_number: int | None = None
    language: str = "en"


class ClauseResult(BaseModel):
    type: str = "unknown"
    clause_type: str = "unknown"
    title: str = "Clause"
    status: str = "partial"
    risk_level: str = "medium"
    summary: str = ""
    business_impact: str = ""
    evidence: list[EvidenceQuote] = Field(default_factory=list)
    evidence_quotes: list[str] = Field(default_factory=list)
    confidence: str = "Medium"
    simple_explanation: str = ""
    why_it_matters: str = ""
    risk_in_plain_english: str = ""
    what_to_check_next: str = ""
    recommended_fix: str = ""
    questions_to_ask: list[str] = Field(default_factory=list)


class RiskItem(BaseModel):
    severity: str = "medium"
    title: str = "Risk"
    affected_clause: str = "General"
    explanation: str = ""
    suggested_mitigation: str = ""
    evidence: list[EvidenceQuote] = Field(default_factory=list)


class ScoreDimension(BaseModel):
    name: str
    score: float
    explanation: str = ""


class ReviewerCritique(BaseModel):
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    overstatements: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    confidence_adjustment: str = "none"


class ContractAnalysisResult(BaseModel):
    schema_version: str = "hybrid-analysis-v2"
    contract_type: str = "generic_commercial"
    contract_type_confidence: float = 0.0
    language: str = "en"
    health_score: int = 0
    risk_level: str = "High"
    score_dimensions: dict[str, Any] = Field(default_factory=dict)
    clauses: list[ClauseResult] = Field(default_factory=list)
    missing_clauses: list[str] = Field(default_factory=list)
    weak_clauses: list[str] = Field(default_factory=list)
    top_risks: list[RiskItem] = Field(default_factory=list)
    recommended_actions: list[Any] = Field(default_factory=list)
    evidence_trace: list[EvidenceQuote] = Field(default_factory=list)
    model_used: str | None = None
    reviewer_used: bool = False
    degraded_mode: bool = True
    confidence: str = "Low"


class ChatAnswer(BaseModel):
    answer: str = ""
    short_answer: str = ""
    confidence: float = 0.0
    intent: str = "contract_specific"
    evidence: list[EvidenceQuote] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    risk_note: str = ""
    suggested_next_step: str = ""
    language: str = "en"
    model_used: str | None = None
    degraded_mode: bool = True
    is_legal_advice_disclaimer: bool = True


class BenchmarkResult(BaseModel):
    profile_used: str = "Generic commercial contract"
    alignment_score: int = 0
    required_clause_coverage: int = 0
    recommended_clause_coverage: int = 0
    missing_required_clauses: list[str] = Field(default_factory=list)
    missing_recommended_clauses: list[str] = Field(default_factory=list)
    high_risk_gaps: list[str] = Field(default_factory=list)
    suggested_improvements: list[Any] = Field(default_factory=list)
    limitations: str = "Internal template alignment comparison, not live market/legal market data."
    evidence: list[EvidenceQuote] = Field(default_factory=list)
