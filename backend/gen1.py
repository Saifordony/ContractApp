"""Compatibility re-exports for legacy imports."""

from contract_health import (
    analyze_contract,
    analyze_and_evaluate_contract,
    contract_chat,
    evaluate_contract,
    explain_clauses_for_layman,
    extract_text_from_pdf_bytes,
)

__all__ = [
    "analyze_contract",
    "analyze_and_evaluate_contract",
    "contract_chat",
    "evaluate_contract",
    "explain_clauses_for_layman",
    "extract_text_from_pdf_bytes",
]
