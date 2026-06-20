"""Bilingual (EN/AR) prompt builders for the one grounded pipeline.

All prompts force the model to ground output in the supplied CONTEXT and to quote
verbatim, which is what the verification step later checks.
"""
from __future__ import annotations

from typing import Optional

from backend.constants import CLAUSE_TYPES, HEALTH_DIMENSIONS

Message = dict


def _lang_name(language: str) -> str:
    return "Arabic" if language == "ar" else "English"


def extraction_messages(context: str, language: str, correction: Optional[str] = None) -> list[Message]:
    clause_lines = "\n".join(
        f"- {c['key']}: {c['label']['en']} / {c['label']['ar']}" for c in CLAUSE_TYPES
    )
    schema = (
        '{"clauses":[{"key":"<clause key>",'
        '"status":"found|partially_found|needs_review|not_found",'
        '"quote":"<verbatim text copied from CONTEXT, empty string if not_found>",'
        '"explanation":"<plain-language meaning of the clause>"}]}'
    )
    system = (
        "You are a meticulous bilingual contract-analysis assistant. "
        "You extract clauses ONLY from the provided CONTEXT and never invent text. "
        "Every quote must be copied verbatim, character-for-character, from the CONTEXT. "
        f"Write every explanation in {_lang_name(language)}."
    )
    instruction = (
        f"Identify each of these clauses in the contract:\n{clause_lines}\n\n"
        "Choose a status for every clause key:\n"
        "- found: clearly and fully present\n"
        "- partially_found: present but incomplete or ambiguous\n"
        "- needs_review: possibly present but unclear\n"
        "- not_found: absent from the CONTEXT\n\n"
        "Rules:\n"
        "1. 'quote' MUST be an exact substring of the CONTEXT. If you cannot copy exact "
        "text, set status to needs_review or not_found and leave quote empty.\n"
        "2. 'explanation' must simplify the clause in plain language a non-lawyer "
        "understands — do not just restate the legal wording.\n"
        f"3. Return ONLY a JSON object matching this schema:\n{schema}"
    )
    if correction:
        instruction += f"\n\nIMPORTANT CORRECTION: {correction}"
    user = f"CONTEXT:\n{context}\n\n{instruction}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def health_messages(context: str, clause_summary: str, language: str,
                    correction: Optional[str] = None) -> list[Message]:
    dim_lines = "\n".join(
        f"- {d['key']}: {d['label']['en']} / {d['label']['ar']}" for d in HEALTH_DIMENSIONS
    )
    schema = (
        '{"overall_score":<int 0-100>,"dimensions":[{"key":"<dimension key>",'
        '"score":<int 0-100>,"explanation":"<why this score>",'
        '"quote":"<verbatim supporting text from CONTEXT, empty if none>"}]}'
    )
    system = (
        "You are a contract-quality assessor. You score a contract's health using ONLY "
        "the provided CONTEXT and clause findings. Support each score with verbatim "
        f"evidence copied from the CONTEXT. Write explanations in {_lang_name(language)}."
    )
    instruction = (
        f"Score these dimensions 0-100 (higher is healthier):\n{dim_lines}\n\n"
        f"Clause findings so far: {clause_summary}\n\n"
        "Rules:\n"
        "1. 'quote' must be an exact substring of the CONTEXT or empty.\n"
        "2. 'overall_score' should reflect the dimension scores.\n"
        f"3. Return ONLY a JSON object matching this schema:\n{schema}"
    )
    if correction:
        instruction += f"\n\nIMPORTANT CORRECTION: {correction}"
    user = f"CONTEXT:\n{context}\n\n{instruction}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def chat_messages(context: str, question: str, language: str,
                  history: Optional[list[dict]] = None) -> list[Message]:
    system = (
        "You are a contract assistant. Answer the user's question using ONLY the "
        "provided CONTEXT. If the answer is not in the CONTEXT, say you could not find "
        "it in this contract. Whenever you state something from the contract, support it "
        'by including the exact source text in double quotes, e.g. "...". '
        f"Answer in {_lang_name(language)}. Be concise and practical."
    )
    convo = ""
    if history:
        for turn in history[-4:]:
            role = "User" if turn.get("role") == "user" else "Assistant"
            convo += f"{role}: {turn.get('content', '')}\n"
    user = f"CONTEXT:\n{context}\n\n{convo}User question: {question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
