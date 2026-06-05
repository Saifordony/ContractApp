from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class TextChunk:
    chunk_id: str
    text: str
    location: str
    start_offset: int
    end_offset: int


SYNONYM_MAP: Dict[str, List[str]] = {
    "law": ["governing law", "jurisdiction", "laws"],
    "governs": ["governing", "jurisdiction"],
    "jurisdiction": ["governing law", "law", "governed"],
    "payment": ["invoice", "fee", "price", "compensation", "pay", "الدفع", "الرسوم", "المقابل", "الراتب"],
    "terminate": ["termination", "end", "cancel", "إنهاء", "فسخ", "مدة العقد"],
    "confidential": ["non-disclosure", "nda", "privacy", "سرية", "المعلومات السرية"],
    "liability": ["damages", "cap", "indemnity", "مسؤولية", "حدود المسؤولية"],
}


LEGAL_QUESTION_HINTS = {
    "contract", "clause", "agreement", "salary", "payment", "invoice", "leave",
    "vacation", "sick", "notice", "termination", "resignation", "overtime",
    "benefits", "working", "hours", "liability", "confidential", "governing", "law",
    "dispute", "arbitration", "renewal", "probation", "penalty", "obligation",
    "عقد", "بند", "إجازة", "راتب", "دفع", "إنهاء", "إشعار", "سرية", "تحكيم", "قانون",
}

PERSONAL_NONLEGAL_HINTS = {
    "feel", "tired", "sad", "stressed", "depressed", "anxious", "tomorrow",
    "donot", "dont", "don't", "can i do", "what can i do", "life", "motivation",
    "لا", "اشعر", "ماذا افعل", "غدا", "حياتي", "نفسي",
}


INTENT_KEYWORDS: Dict[str, set[str]] = {
    "leave_policy": {"leave", "vacation", "sick", "absence", "day off", "time off", "إجازة", "اجازة", "مرضية", "عطلة"},
    "working_hours": {"hours", "schedule", "shift", "overtime", "week", "ساعات", "دوام", "إضافي"},
    "compensation": {"salary", "payment", "invoice", "bonus", "compensation", "pay", "راتب", "الدفع", "الرسوم", "المقابل المالي"},
    "termination": {"terminate", "termination", "resign", "notice", "end", "إنهاء", "فسخ", "إشعار", "مدة العقد"},
    "confidentiality": {"confidential", "nda", "non-disclosure", "disclose", "سرية", "المعلومات السرية"},
    "governing_law": {"law", "jurisdiction", "court", "arbitration", "dispute", "القانون", "النظام", "المحكمة", "تحكيم", "المنازعات"},
    "obligations": {"must", "obligation", "required", "responsibility", "deliverable", "التزامات", "مسؤوليات", "الخدمة"},
}

@dataclass
class RetrievalHit:
    score: float
    chunk: TextChunk
    lexical_score: float
    semantic_score: float


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[\u0600-\u06FFa-zA-Z0-9_\-']+", (text or "").lower())


def _expand_query_tokens(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    for token in list(tokens):
        for synonym in SYNONYM_MAP.get(token, []):
            expanded.update(_tokenize(synonym))
    return expanded


def chunk_contract_text(contract_text: str, chunk_size: int = 900) -> List[TextChunk]:
    text = (contract_text or "").strip()
    if not text:
        return []

    lines = [line.rstrip() for line in text.splitlines()]
    chunks: List[TextChunk] = []

    current = []
    current_heading = "Document"
    current_start = 0
    cursor = 0
    chunk_index = 1

    def flush_chunk(end_cursor: int):
        nonlocal chunk_index, current, current_start
        joined = "\n".join([l for l in current if l is not None]).strip()
        if not joined:
            return
        chunks.append(
            TextChunk(
                chunk_id=f"chunk-{chunk_index}",
                text=joined,
                location=f"section:{current_heading};offset:{current_start}-{end_cursor}",
                start_offset=current_start,
                end_offset=end_cursor,
            )
        )
        chunk_index += 1

    def is_heading(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if re.match(r"^\d+(\.\d+)*\s+", stripped):
            return True
        if len(stripped) <= 90 and stripped.upper() == stripped and any(ch.isalpha() for ch in stripped):
            return True
        return False

    for line in lines:
        line_len = len(line) + 1
        if is_heading(line):
            if current:
                flush_chunk(cursor)
                current = []
            current_heading = line.strip()
            current_start = cursor

        current.append(line)
        joined_len = sum(len(l) + 1 for l in current)
        if joined_len >= chunk_size:
            flush_chunk(cursor + line_len)
            current = []
            current_start = cursor + line_len

        cursor += line_len

    if current:
        flush_chunk(cursor)

    return chunks


def _idf_lookup(chunks: List[TextChunk]) -> Dict[str, float]:
    total_docs = max(len(chunks), 1)
    doc_freq: Dict[str, int] = {}
    for chunk in chunks:
        unique = set(_tokenize(chunk.text))
        for tok in unique:
            doc_freq[tok] = doc_freq.get(tok, 0) + 1
    return {tok: math.log(1 + total_docs / (1 + df)) for tok, df in doc_freq.items()}


def retrieve_relevant_chunks_with_scores(
    question: str,
    chunks: List[TextChunk],
    top_k: int = 4,
) -> List[Tuple[float, TextChunk]]:
    base_tokens = set(_tokenize(question))
    q_tokens = _expand_query_tokens(base_tokens)
    if not q_tokens:
        return [(1.0, chunk) for chunk in chunks[:top_k]]

    idf = _idf_lookup(chunks)
    scored: List[RetrievalHit] = []
    q_lower = (question or "").lower()

    for chunk in chunks:
        c_tokens = _tokenize(chunk.text)
        if not c_tokens:
            continue

        c_token_set = set(c_tokens)
        overlap = q_tokens & c_token_set
        lexical = len(overlap) / max(len(q_tokens), 1)

        tf_bonus = 0.0
        for token in overlap:
            tf_bonus += min(0.12, c_tokens.count(token) * 0.02 * (1 + idf.get(token, 0.0)))

        phrase_bonus = 0.14 if q_lower and q_lower in chunk.text.lower() else 0.0

        semantic = 0.0
        for token in base_tokens:
            for syn in SYNONYM_MAP.get(token, []):
                syn_tokens = set(_tokenize(syn))
                if syn_tokens & c_token_set:
                    semantic += 0.06

        score = lexical + tf_bonus + phrase_bonus + semantic
        if score > 0:
            scored.append(
                RetrievalHit(
                    score=round(score, 4),
                    chunk=chunk,
                    lexical_score=round(lexical, 4),
                    semantic_score=round(semantic, 4),
                )
            )

    scored.sort(key=lambda item: item.score, reverse=True)
    return [(hit.score, hit.chunk) for hit in scored[:top_k]]


def retrieve_relevant_chunks(question: str, chunks: List[TextChunk], top_k: int = 4) -> List[TextChunk]:
    return [chunk for _, chunk in retrieve_relevant_chunks_with_scores(question, chunks, top_k)]


def _extract_sentences_with_keywords(text: str, question_tokens: set[str], limit: int = 3) -> List[str]:
    sentences = re.split(r"(?<=[\.!?])\s+", text)
    picked: List[str] = []
    for sentence in sentences:
        st = sentence.strip()
        if not st:
            continue
        st_tokens = set(_tokenize(st))
        if question_tokens & st_tokens:
            picked.append(st)
        if len(picked) >= limit:
            break
    return picked




SKILLS_NOISE_HINTS = {"git", "agile", "problem-solving", "communication skills", "version control", "probation period", "job description", "requirements", "experience with"}


def _is_skills_noise(text: str) -> bool:
    t=(text or "").lower()
    return any(h in t for h in SKILLS_NOISE_HINTS)



CLAUSE_PLAIN_ENGLISH = {
    "parties": "Identifies who is bound by the contract.",
    "effective_date": "Shows when the contract starts or becomes binding.",
    "termination": "Explains how the contract can end and what notice is required.",
    "compensation": "Explains pay, fees, salary, or other payment terms.",
    "leave_policy": "Explains vacation, sick leave, holidays, or time-off rights.",
    "working_hours": "Explains expected work hours, schedule, or overtime terms.",
    "confidentiality": "Explains how private information must be protected.",
    "governing_law": "Shows which law applies to the contract.",
    "dispute_resolution": "Explains how disagreements will be handled.",
    "renewal": "Explains whether and how the contract continues after the first term.",
}


def _clause_plain_summary(clause_name: str, text: str | None) -> str:
    if not text:
        return "No reliable wording was found for this clause."
    return f"This section appears to cover {clause_name.replace('_', ' ')}. Review the evidence to confirm it matches the business deal."


def _clause_why_it_matters(clause_name: str) -> str:
    return CLAUSE_PLAIN_ENGLISH.get(clause_name, "This clause helps clarify rights, duties, timing, or risk in the contract.")

def _validated_clause_record(clause_name: str, matches: list[dict], source_text: str = "") -> Dict[str, Any]:
    issues: List[str] = []
    if not matches:
        if clause_name == "parties" and _is_skills_noise(source_text):
            return {
                "status": "not_found",
                "confidence": 0.0,
                "extracted_text": None,
                "evidence_snippets": [],
                "issues": ["Rejected because text appears to be skills/job-description content, not contracting party evidence."],
                "plain_english_summary": _clause_plain_summary(clause_name, None),
                "what_was_found": "No reliable evidence found.",
                "why_it_matters": _clause_why_it_matters(clause_name),
                "missing_information": ["Clear party-identification wording."],
                "recommended_action": "Look for party-identification language (for example, 'between X and Y', legal entity names, or defined party terms).",
            }
        return {
            "status": "not_found",
            "confidence": 0.0,
            "extracted_text": None,
            "evidence_snippets": [],
            "issues": ["No reliable evidence found for this clause."],
            "plain_english_summary": _clause_plain_summary(clause_name, None),
            "what_was_found": "No reliable evidence found.",
            "why_it_matters": _clause_why_it_matters(clause_name),
            "missing_information": [f"Clear {clause_name.replace('_', ' ')} wording."],
            "recommended_action": "Add clear wording for this clause or ask a reviewer to confirm whether it exists elsewhere in the contract.",
        }

    top = matches[0]
    top_quote = str(top.get("quote", ""))

    if clause_name == "parties" and _is_skills_noise(top_quote):
        return {
            "status": "not_found",
            "confidence": 0.0,
            "extracted_text": None,
            "evidence_snippets": [],
            "issues": ["Rejected because text appears to be skills/job-description content, not contracting party evidence."],
            "plain_english_summary": _clause_plain_summary(clause_name, None),
            "what_was_found": "No reliable evidence found.",
            "why_it_matters": _clause_why_it_matters(clause_name),
            "missing_information": ["Clear party-identification wording."],
            "recommended_action": "Look for party-identification language (for example, 'between X and Y', legal entity names, or defined party terms).",
        }

    ev=[{"quote":m.get("quote",""),"location":m.get("location",""),"chunk_id":m.get("chunk_id","")} for m in matches[:2]]
    confidence = 0.86 if len(matches) > 1 else 0.72
    return {
        "status": "found",
        "confidence": confidence,
        "extracted_text": top_quote,
        "what_was_found": top_quote,
        "plain_english_summary": _clause_plain_summary(clause_name, top_quote),
        "why_it_matters": _clause_why_it_matters(clause_name),
        "evidence_snippets": ev,
        "issues": issues,
        "missing_information": [],
        "recommended_action": "No immediate action required. Confirm the wording matches the intended business agreement.",
    }


def extract_key_clauses(contract_text: str) -> Dict[str, Any]:
    chunks = chunk_contract_text(contract_text)
    clause_map = {
        "parties": ["party", "parties", "between", "الأطراف", "طرف", "بين"],
        "effective_date": ["effective", "date", "تاريخ", "سريان", "نافذ"],
        "term": ["term", "duration", "مدة العقد", "المدة"],
        "renewal": ["renew", "automatic renewal", "تجديد", "يتجدد"],
        "termination": ["termination", "terminate", "إنهاء", "انهاء", "فسخ", "مدة العقد"],
        "payment_terms": ["payment", "invoice", "fees", "الدفع", "الرسوم", "المقابل المالي", "راتب", "الأجر"],
        "liability": ["liability", "damages", "limit", "مسؤولية", "حدود المسؤولية", "تعويض"],
        "confidentiality": ["confidential", "confidentiality", "سرية", "المعلومات السرية"],
        "governing_law": ["governing law", "law", "jurisdiction", "القانون الواجب التطبيق", "النظام المطبق", "القانون"],
        "dispute_resolution": ["dispute", "arbitration", "mediation", "المنازعات", "تسوية النزاعات", "تحكيم", "وساطة"],
        "sla_obligations": ["service level", "sla", "obligation", "deliverable", "التزامات", "مستوى الخدمة", "الخدمات"],
        "penalties": ["penalty", "liquidated damages", "late fee", "غرامة", "جزاء", "تعويضات"],
        "change_control": ["change", "amendment", "change order", "تعديل", "أمر تغيير"],
    }

    extracted: Dict[str, Dict[str, Any]] = {}
    conflicts: List[Dict[str, Any]] = []

    for clause_name, keywords in clause_map.items():
        matches = []
        for chunk in chunks:
            lower = chunk.text.lower()
            if any(keyword in lower for keyword in keywords):
                matches.append(
                    {
                        "quote": chunk.text[:280],
                        "location": chunk.location,
                        "chunk_id": chunk.chunk_id,
                    }
                )

        extracted[clause_name] = _validated_clause_record(clause_name, matches, contract_text)

        unique_quotes = {m["quote"] for m in matches[:3]}
        if len(unique_quotes) > 1 and clause_name in {"term", "renewal", "payment_terms", "termination"}:
            conflicts.append(
                {
                    "clause": clause_name,
                    "status": "conflict",
                    "evidence": matches[:2],
                }
            )

    return {
        "clauses": extracted,
        "conflicts": conflicts,
        "chunk_count": len(chunks),
    }


def _build_risk_flags(text: str, evidence: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    lower = text.lower()
    flags: List[Dict[str, Any]] = []

    if "unlimited liability" in lower or "without limitation" in lower:
        flags.append({"type": "unlimited_liability", "severity": "high", "evidence": evidence[:1]})
    if "automatic renewal" in lower and "notice" not in lower:
        flags.append({"type": "auto_renewal_without_notice", "severity": "medium", "evidence": evidence[:1]})
    if "governing law" not in lower:
        flags.append({"type": "missing_governing_law", "severity": "high", "evidence": evidence[:1] if evidence else []})

    return flags


def _best_evidence_quotes(chunk: TextChunk, question_tokens: set[str], limit: int = 2) -> List[str]:
    sentences = re.split(r"(?<=[\.!?])\s+", chunk.text)
    ranked: List[Tuple[int, str]] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        tokens = set(_tokenize(sentence))
        score = len(tokens & question_tokens)
        if score > 0:
            ranked.append((score, sentence[:260]))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [sent for _, sent in ranked[:limit]]




def _is_out_of_scope_personal_question(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return True

    q_tokens = set(_tokenize(q))
    has_legal_signal = bool(q_tokens & LEGAL_QUESTION_HINTS)

    has_personal_signal = any(hint in q for hint in PERSONAL_NONLEGAL_HINTS)

    return has_personal_signal and not has_legal_signal






def _is_arabic_response(response_language: str) -> bool:
    lang = (response_language or "english").strip().lower()
    return lang in {"arabic", "ar", "ara", "العربية", "arab"}


def _msg(en: str, ar: str, response_language: str) -> str:
    return ar if _is_arabic_response(response_language) else en


def classify_question_intent(question: str) -> str:
    q_tokens = set(_tokenize(question))
    scored: List[Tuple[int, str]] = []
    for intent, keywords in INTENT_KEYWORDS.items():
        score = len(q_tokens & {tok for kw in keywords for tok in _tokenize(kw)})
        scored.append((score, intent))
    scored.sort(reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else "general_contract"


def follow_ups_for_intent(intent: str, response_language: str = "english") -> List[str]:
    mapping = {
        "leave_policy": [
            "Do you want the exact leave entitlement and approval steps from your contract?",
            "Should I summarize sick leave vs annual leave separately?",
        ],
        "working_hours": [
            "Should I extract standard hours and overtime compensation terms?",
            "Do you want a plain-language summary of attendance obligations?",
        ],
        "compensation": [
            "Do you want payment timing, method, and late-payment terms extracted exactly?",
            "Should I summarize salary/fees and any deductions in simple terms?",
        ],
        "termination": [
            "Should I list notice periods and who can terminate under what conditions?",
            "Do you want a risk summary of one-sided termination clauses?",
        ],
        "confidentiality": [
            "Should I summarize what information is protected and for how long?",
            "Do you want exceptions and breach consequences extracted?",
        ],
        "governing_law": [
            "Should I extract governing law, jurisdiction, and dispute forum clauses?",
            "Do you want a plain-language explanation of arbitration vs court language?",
        ],
    }
    selected = mapping.get(
        intent,
        [
            "Do you want me to summarize only the obligations that apply to you?",
            "Should I extract the exact clause text and provide a plain-language interpretation?",
        ],
    )
    if _is_arabic_response(response_language):
        ar_map = {
            "Do you want the exact leave entitlement and approval steps from your contract?": "هل تريد استخراج استحقاق الإجازات وخطوات الموافقة كما وردت في العقد؟",
            "Should I summarize sick leave vs annual leave separately?": "هل ألخّص لك الإجازة المرضية مقابل الإجازة السنوية بشكل منفصل؟",
            "Should I extract standard hours and overtime compensation terms?": "هل تريد استخراج ساعات العمل الأساسية وشروط تعويض العمل الإضافي؟",
            "Do you want a plain-language summary of attendance obligations?": "هل تريد ملخصًا مبسطًا لالتزامات الحضور والانضباط؟",
            "Do you want payment timing, method, and late-payment terms extracted exactly?": "هل تريد استخراج مواعيد الدفع والطريقة وشروط التأخير بشكل دقيق؟",
            "Should I summarize salary/fees and any deductions in simple terms?": "هل ألخّص الراتب/الرسوم وأي استقطاعات بلغة بسيطة؟",
            "Should I list notice periods and who can terminate under what conditions?": "هل تريد قائمة بفترات الإشعار ومن يملك حق الإنهاء وتحت أي شروط؟",
            "Do you want a risk summary of one-sided termination clauses?": "هل تريد ملخص مخاطر البنود أحادية الجانب في الإنهاء؟",
            "Should I summarize what information is protected and for how long?": "هل ألخّص ما هي المعلومات المحمية ولمدة كم؟",
            "Do you want exceptions and breach consequences extracted?": "هل تريد استخراج الاستثناءات ونتائج الإخلال؟",
            "Should I extract governing law, jurisdiction, and dispute forum clauses?": "هل تريد استخراج القانون الواجب التطبيق والاختصاص القضائي وآلية فض النزاع؟",
            "Do you want a plain-language explanation of arbitration vs court language?": "هل تريد شرحًا مبسطًا للفرق بين التحكيم والتقاضي في صياغة العقد؟",
            "Do you want me to summarize only the obligations that apply to you?": "هل تريد أن ألخّص فقط الالتزامات التي تنطبق عليك؟",
            "Should I extract the exact clause text and provide a plain-language interpretation?": "هل تريد استخراج نص البند حرفيًا ثم تقديم تفسير مبسط له؟",
        }
        return [ar_map.get(item, item) for item in selected]
    return selected


def answer_contract_question(contract_text: str, question: str, response_language: str = "english") -> Dict[str, Any]:
    if _is_out_of_scope_personal_question(question):
        return {
            "answer": _msg("I can only answer contract-related questions. I can’t give personal life advice.", "يمكنني الإجابة فقط عن الأسئلة المتعلقة بالعقد، ولا أقدّم نصائح شخصية.", response_language),
            "confidence": 0.0,
            "evidence": [],
            "not_found": [question],
            "follow_up_questions": [
                _msg("Try asking: What does my contract say about leave, sick days, or notice?", "جرّب أن تسأل: ماذا ينص عقدي بخصوص الإجازات المرضية أو السنوية أو فترات الإشعار؟", response_language),
                _msg("Try asking: Can I take unpaid leave and what notice is required?", "جرّب أن تسأل: هل يمكنني أخذ إجازة غير مدفوعة وما فترة الإشعار المطلوبة؟", response_language),
            ],
            "risk_flags": _build_risk_flags(contract_text, []),
            "retrieved_chunk_ids": [],
            "retrieval_scores": [],
            "intent": "out_of_scope",
        }

    intent = classify_question_intent(question)
    chunks = chunk_contract_text(contract_text)
    scored_chunks = retrieve_relevant_chunks_with_scores(question, chunks)

    if not scored_chunks:
        return {
            "answer": _msg("Not Found in the provided contract text.", "غير موجود في نص العقد المقدم.", response_language),
            "confidence": 0.0,
            "evidence": [],
            "not_found": [question],
            "follow_up_questions": [_msg("Can you provide the exact clause title to check?", "هل يمكنك ذكر عنوان البند بدقة حتى أتحقق منه؟", response_language)],
            "risk_flags": [],
            "retrieved_chunk_ids": [],
            "retrieval_scores": [],
            "intent": intent,
        }

    top_score = scored_chunks[0][0]
    question_tokens = _expand_query_tokens(set(_tokenize(question)))

    if top_score < 0.28:
        return {
            "answer": _msg("Not Found in the provided contract text.", "غير موجود في نص العقد المقدم.", response_language),
            "confidence": 0.1,
            "evidence": [],
            "not_found": [question],
            "follow_up_questions": [
                _msg("Can you rephrase with a clause title (e.g., termination, payment, confidentiality)?", "هل يمكنك إعادة الصياغة مع ذكر اسم البند (مثل الإنهاء، الدفع، السرية)؟", response_language),
                _msg("Do you want me to list related clauses that might partially address this?", "هل تريد أن أسرد البنود ذات الصلة التي قد تعالج هذا بشكل جزئي؟", response_language),
            ],
            "risk_flags": _build_risk_flags(contract_text, []),
            "retrieved_chunk_ids": [chunk.chunk_id for _, chunk in scored_chunks],
            "retrieval_scores": [score for score, _ in scored_chunks],
            "intent": intent,
        }

    evidence: List[Dict[str, str]] = []
    answer_sentences: List[str] = []

    for score, chunk in scored_chunks:
        best_quotes = _best_evidence_quotes(chunk, question_tokens, limit=2)
        if not best_quotes:
            continue
        for quote in best_quotes:
            evidence.append({"quote": quote, "location": chunk.location})
            answer_sentences.append(quote)

    answer_sentences = list(dict.fromkeys(answer_sentences))

    if not answer_sentences:
        answer = _msg("Not Found in the provided contract text.", "غير موجود في نص العقد المقدم.", response_language)
        confidence = 0.15
        not_found = [question]
    else:
        answer = _msg("Based on your contract: ", "استنادًا إلى عقدك: ", response_language) + " ".join(answer_sentences[:2])
        confidence = min(0.97, max(0.25, top_score))
        not_found = []

    follow_ups = follow_ups_for_intent(intent, response_language=response_language)

    risk_flags = _build_risk_flags(contract_text, evidence)

    return {
        "answer": answer,
        "confidence": round(confidence, 2),
        "evidence": evidence[:3],
        "not_found": not_found,
        "follow_up_questions": follow_ups,
        "risk_flags": risk_flags,
        "retrieved_chunk_ids": [chunk.chunk_id for _, chunk in scored_chunks],
        "retrieval_scores": [score for score, _ in scored_chunks],
        "intent": intent,
    }
