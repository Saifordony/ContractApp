from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import statistics
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree

import fitz
from pydantic import BaseModel, Field, ValidationError

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


CLAUSE_WEIGHTS: Dict[str, float] = {
    "payment_terms": 1.2,
    "termination": 1.1,
    "liability": 1.2,
    "confidentiality": 1.0,
    "governing_law": 0.8,
    "dispute_resolution": 0.8,
    "renewal": 0.7,
    "change_control": 0.6,
    "sla_obligations": 0.9,
    "misc": 0.4,
}


class BenchmarkCitation(BaseModel):
    benchmark_clause_id: str
    snippet_used: str


class ClauseBenchmarkResult(BaseModel):
    clause_id: str
    clause_type: str
    alignment_label: str
    benchmark_stats: Dict[str, Any]
    typical_patterns: List[str]
    explanation: str
    suggested_revision: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    citations: List[BenchmarkCitation]


class BenchmarkAnalyzeResponse(BaseModel):
    contract_id: str
    overall_score: int = Field(ge=0, le=100)
    clause_results: List[ClauseBenchmarkResult]
    meta: Dict[str, Any]


@dataclass
class BenchmarkClause:
    benchmark_clause_id: str
    contract_type: str
    jurisdiction: str
    industry: Optional[str]
    clause_type: str
    snippet: str
    embedding: List[float]
    numeric_features: Dict[str, float]
    source: str = "seed"


@dataclass
class UserClause:
    clause_id: str
    clause_type: str
    text: str
    location: str
    embedding: List[float]
    numeric_features: Dict[str, float]


class InMemoryVectorStore:
    def __init__(self):
        self._clauses: List[BenchmarkClause] = []

    def clear(self) -> None:
        self._clauses.clear()

    def add(self, clause: BenchmarkClause) -> None:
        self._clauses.append(clause)

    def all(self) -> List[BenchmarkClause]:
        return list(self._clauses)

    def search(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Dict[str, Any],
    ) -> List[Tuple[float, BenchmarkClause]]:
        candidates = self._clauses
        for key, value in filters.items():
            if value is None:
                continue
            candidates = [c for c in candidates if getattr(c, key) == value]

        scored: List[Tuple[float, BenchmarkClause]] = []
        for clause in candidates:
            score = cosine_similarity(query_embedding, clause.embedding)
            scored.append((score, clause))

        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:top_k]


GLOBAL_VECTOR_STORE = InMemoryVectorStore()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    num = sum(x * y for x, y in zip(a, b))
    den_a = math.sqrt(sum(x * x for x in a))
    den_b = math.sqrt(sum(y * y for y in b))
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / (den_a * den_b)


def embed_text(text: str) -> List[float]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and OpenAI is not None:
        try:
            client = OpenAI(api_key=api_key)
            resp = client.embeddings.create(model="text-embedding-3-small", input=text[:8000])
            return list(resp.data[0].embedding)
        except Exception:
            pass

    # deterministic local fallback for tests / offline environments
    dim = 128
    vec = [0.0] * dim
    tokens = re.findall(r"[a-zA-Z0-9_\-']+", (text or "").lower())
    if not tokens:
        return vec

    for tok in tokens:
        idx = int(hashlib.sha256(tok.encode()).hexdigest(), 16) % dim
        vec[idx] += 1.0

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def parse_contract_file(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        with fitz.open(stream=data, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc).strip()

    if name.endswith(".docx"):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml_data = zf.read("word/document.xml")
        root = ElementTree.fromstring(xml_data)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts = [node.text for node in root.findall(".//w:t", ns) if node.text]
        return "\n".join(texts).strip()

    # treat as plain text fallback
    return data.decode("utf-8", errors="ignore").strip()


def split_clauses(contract_text: str) -> List[Tuple[str, str, str]]:
    lines = [ln.strip() for ln in contract_text.splitlines() if ln.strip()]
    if not lines:
        return []

    clauses: List[Tuple[str, str, str]] = []
    current_title = "preamble"
    current_body: List[str] = []
    start_idx = 0

    heading_pattern = re.compile(r"^(\d+(\.\d+)*\s+)?([A-Z][A-Za-z\s/&-]{2,}|[A-Z\s]{4,})$")

    for idx, line in enumerate(lines):
        is_heading = bool(heading_pattern.match(line)) and len(line.split()) <= 8
        if is_heading and current_body:
            text = " ".join(current_body).strip()
            clauses.append((current_title, text, f"line:{start_idx}-{idx}"))
            current_title = line.lower()
            current_body = []
            start_idx = idx
        elif is_heading and not current_body:
            current_title = line.lower()
            start_idx = idx
        else:
            current_body.append(line)

    if current_body:
        clauses.append((current_title, " ".join(current_body).strip(), f"line:{start_idx}-{len(lines)}"))

    return clauses


def classify_clause_type(title: str, text: str) -> str:
    combined = f"{title} {text}".lower()
    mapping = {
        "payment_terms": ["payment", "invoice", "fee", "compensation"],
        "termination": ["termination", "terminate", "end this agreement"],
        "liability": ["liability", "damages", "indemn"],
        "confidentiality": ["confidential", "non-disclosure"],
        "governing_law": ["governing law", "jurisdiction", "applicable law"],
        "dispute_resolution": ["dispute", "arbitration", "mediation"],
        "renewal": ["renewal", "auto-renew", "automatic renewal"],
        "change_control": ["change control", "change order", "amendment"],
        "sla_obligations": ["service level", "sla", "uptime", "obligation", "deliverable"],
    }
    for label, patterns in mapping.items():
        if any(pat in combined for pat in patterns):
            return label
    return "misc"


def extract_numeric_features(text: str) -> Dict[str, float]:
    lower = text.lower()
    out: Dict[str, float] = {}

    day_match = re.search(r"(\d{1,3})\s*day", lower)
    if day_match:
        out["notice_days"] = float(day_match.group(1))

    pay_match = re.search(r"(\d{1,3})\s*days?\s*of\s*invoice", lower)
    if pay_match:
        out["payment_days"] = float(pay_match.group(1))

    cap_match = re.search(r"(\d+(?:\.\d+)?)\s*%", lower)
    if cap_match:
        out["liability_cap_percent"] = float(cap_match.group(1))

    return out


def _compute_percentiles(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"p25": 0.0, "median": 0.0, "p75": 0.0}
    vals = sorted(values)
    median = statistics.median(vals)
    p25 = vals[max(0, int(0.25 * (len(vals) - 1)))]
    p75 = vals[min(len(vals) - 1, int(0.75 * (len(vals) - 1)))]
    return {"p25": float(p25), "median": float(median), "p75": float(p75)}


def _score_clause_alignment(
    clause_type: str,
    similarity_scores: List[float],
    numeric_features: Dict[str, float],
    benchmark_numeric_values: Dict[str, List[float]],
) -> Tuple[int, str]:
    sim_component = int(100 * (sum(similarity_scores) / max(len(similarity_scores), 1)))

    numeric_component = 100
    penalties = 0
    for key, vals in benchmark_numeric_values.items():
        if not vals or key not in numeric_features:
            continue
        med = statistics.median(vals)
        user_val = numeric_features[key]
        if med == 0:
            continue
        deviation = abs(user_val - med) / abs(med)
        if deviation > 0.75:
            penalties += 35
        elif deviation > 0.4:
            penalties += 20
        elif deviation > 0.2:
            penalties += 8

    numeric_component = max(0, numeric_component - penalties)
    weight = CLAUSE_WEIGHTS.get(clause_type, 0.6)
    final_score = int((sim_component * 0.65 + numeric_component * 0.35) * weight)
    final_score = max(0, min(100, final_score))

    if final_score >= 70:
        label = "green"
    elif final_score >= 45:
        label = "yellow"
    else:
        label = "red"

    return final_score, label


def _summarize_typical_patterns(retrieved: List[Tuple[float, BenchmarkClause]]) -> List[str]:
    snippets = [clause.snippet for _, clause in retrieved[:3]]
    patterns = []
    for snip in snippets:
        sentence = re.split(r"(?<=[\.!?])\s+", snip.strip())[0]
        if sentence and sentence not in patterns:
            patterns.append(sentence[:180])
    return patterns[:3]


def _generate_explanation(
    clause_type: str,
    score: int,
    label: str,
    benchmark_stats: Dict[str, Any],
    evidence_ids: List[str],
) -> str:
    return (
        f"Clause type '{clause_type}' scored {score}/100 ({label}) against {benchmark_stats.get('N', 0)} peers. "
        f"Assessment is grounded in retrieved benchmark clauses: {', '.join(evidence_ids[:3])}."
    )


def _build_user_clauses(contract_text: str) -> List[UserClause]:
    raw_clauses = split_clauses(contract_text)
    clauses: List[UserClause] = []
    for idx, (title, text, location) in enumerate(raw_clauses, start=1):
        clause_type = classify_clause_type(title, text)
        clauses.append(
            UserClause(
                clause_id=f"user-clause-{idx}",
                clause_type=clause_type,
                text=text,
                location=location,
                embedding=embed_text(text),
                numeric_features=extract_numeric_features(text),
            )
        )
    return clauses


def _retrieve_with_fallbacks(
    store: InMemoryVectorStore,
    user_clause: UserClause,
    contract_type: str,
    jurisdiction: str,
    industry: Optional[str],
    top_k: int = 6,
) -> Tuple[List[Tuple[float, BenchmarkClause]], List[str]]:
    fallbacks: List[str] = []
    filters = {
        "contract_type": contract_type,
        "jurisdiction": jurisdiction,
        "industry": industry,
        "clause_type": user_clause.clause_type,
    }

    retrieved = store.search(user_clause.embedding, top_k, filters)
    if len(retrieved) >= 3:
        return retrieved, fallbacks

    # Relax industry
    if filters.get("industry") is not None:
        filters["industry"] = None
        fallbacks.append("relaxed_industry")
        retrieved = store.search(user_clause.embedding, top_k, filters)
        if len(retrieved) >= 3:
            return retrieved, fallbacks

    # Relax jurisdiction
    filters["jurisdiction"] = None
    fallbacks.append("relaxed_jurisdiction")
    retrieved = store.search(user_clause.embedding, top_k, filters)
    if len(retrieved) >= 3:
        return retrieved, fallbacks

    # Relax contract_type
    filters["contract_type"] = None
    fallbacks.append("relaxed_contract_type")
    retrieved = store.search(user_clause.embedding, top_k, filters)
    if len(retrieved) >= 2:
        return retrieved, fallbacks

    # Last resort: relax clause type
    filters["clause_type"] = None
    fallbacks.append("relaxed_clause_type")
    retrieved = store.search(user_clause.embedding, top_k, filters)
    return retrieved, fallbacks


def ingest_seed_dataset(seed_items: List[Dict[str, Any]], clear_first: bool = False) -> Dict[str, Any]:
    if clear_first:
        GLOBAL_VECTOR_STORE.clear()

    ingested = 0
    for item in seed_items:
        snippet = item.get("snippet", "").strip()
        if not snippet:
            continue
        clause = BenchmarkClause(
            benchmark_clause_id=str(item.get("benchmark_clause_id", f"seed-{ingested+1}")),
            contract_type=str(item.get("contract_type", "general")),
            jurisdiction=str(item.get("jurisdiction", "global")),
            industry=item.get("industry"),
            clause_type=str(item.get("clause_type", "misc")),
            snippet=snippet,
            embedding=embed_text(snippet),
            numeric_features=item.get("numeric_features", {}) or extract_numeric_features(snippet),
            source=str(item.get("source", "seed")),
        )
        GLOBAL_VECTOR_STORE.add(clause)
        ingested += 1

    return {"ingested": ingested, "total": len(GLOBAL_VECTOR_STORE.all())}


def load_seed_from_repo() -> Dict[str, Any]:
    seed_path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "benchmark_seed.json"
    if not seed_path.exists():
        return {"ingested": 0, "total": len(GLOBAL_VECTOR_STORE.all()), "source": "missing_seed_file"}
    items = json.loads(seed_path.read_text())
    result = ingest_seed_dataset(items, clear_first=False)
    result["source"] = str(seed_path)
    return result


def run_benchmark_analysis(
    filename: str,
    file_bytes: bytes,
    contract_type: str,
    jurisdiction: str,
    industry: Optional[str],
    opt_in_store_user_data: bool,
) -> Dict[str, Any]:
    contract_text = parse_contract_file(filename, file_bytes)
    if not contract_text.strip():
        raise ValueError("Could not extract contract text from uploaded file")

    # Auto-seed if store empty.
    if not GLOBAL_VECTOR_STORE.all():
        load_seed_from_repo()

    user_clauses = _build_user_clauses(contract_text)
    clause_results: List[Dict[str, Any]] = []
    clause_scores: List[Tuple[int, str]] = []
    peer_sizes: Dict[str, int] = {}
    all_fallbacks: List[str] = []

    for clause in user_clauses:
        retrieved, fallbacks = _retrieve_with_fallbacks(
            GLOBAL_VECTOR_STORE,
            clause,
            contract_type=contract_type,
            jurisdiction=jurisdiction,
            industry=industry,
        )
        all_fallbacks.extend(fallbacks)

        scores = [score for score, _ in retrieved]
        peer_sizes[clause.clause_type] = max(peer_sizes.get(clause.clause_type, 0), len(retrieved))

        numeric_pool: Dict[str, List[float]] = {}
        for _, bench in retrieved:
            for key, val in bench.numeric_features.items():
                numeric_pool.setdefault(key, []).append(float(val))

        benchmark_stats = {
            "N": len(retrieved),
            "p25": {k: _compute_percentiles(v)["p25"] for k, v in numeric_pool.items()},
            "median": {k: _compute_percentiles(v)["median"] for k, v in numeric_pool.items()},
            "p75": {k: _compute_percentiles(v)["p75"] for k, v in numeric_pool.items()},
        }

        score, label = _score_clause_alignment(
            clause.clause_type,
            scores,
            clause.numeric_features,
            numeric_pool,
        )
        clause_scores.append((score, clause.clause_type))

        confidence = 0.15
        if scores:
            confidence = min(0.98, max(0.1, (sum(scores) / len(scores)) * min(1.0, len(scores) / 5)))

        snippets = _summarize_typical_patterns(retrieved)
        cits = [
            {
                "benchmark_clause_id": bench.benchmark_clause_id,
                "snippet_used": bench.snippet[:160],
            }
            for _, bench in retrieved[:3]
        ]

        explanation = _generate_explanation(
            clause.clause_type,
            score,
            label,
            benchmark_stats,
            [c["benchmark_clause_id"] for c in cits],
        )

        suggested_revision = None
        if label in {"yellow", "red"}:
            suggested_revision = (
                f"Consider revising this {clause.clause_type} clause toward benchmark median terms "
                f"for {contract_type}/{jurisdiction} peer contracts."
            )

        avg_similarity = (sum(scores) / len(scores)) if scores else 0.0
        if len(retrieved) < 2 or avg_similarity < 0.22:
            explanation = "Insufficient benchmark evidence for high-confidence comparison."
            confidence = min(confidence, 0.25)
            if label == "green":
                label = "yellow"

        clause_results.append(
            {
                "clause_id": clause.clause_id,
                "clause_type": clause.clause_type,
                "alignment_label": label,
                "benchmark_stats": benchmark_stats,
                "typical_patterns": snippets,
                "explanation": explanation,
                "suggested_revision": suggested_revision,
                "confidence": round(confidence, 2),
                "citations": cits,
            }
        )

        if opt_in_store_user_data:
            GLOBAL_VECTOR_STORE.add(
                BenchmarkClause(
                    benchmark_clause_id=f"user-optin-{hashlib.sha256(clause.text.encode()).hexdigest()[:12]}",
                    contract_type=contract_type,
                    jurisdiction=jurisdiction,
                    industry=industry,
                    clause_type=clause.clause_type,
                    snippet="",  # privacy: never store user clause text
                    embedding=clause.embedding,
                    numeric_features=clause.numeric_features,
                    source="user_opt_in",
                )
            )

    overall_score = 0
    if clause_scores:
        total_weight = sum(CLAUSE_WEIGHTS.get(t, 0.6) for _, t in clause_scores)
        weighted_sum = sum(score * CLAUSE_WEIGHTS.get(t, 0.6) for score, t in clause_scores)
        overall_score = int(max(0, min(100, weighted_sum / max(total_weight, 1e-9))))

    response_payload = {
        "contract_id": hashlib.sha256(contract_text[:2000].encode()).hexdigest()[:16],
        "overall_score": overall_score,
        "clause_results": clause_results,
        "meta": {
            "peer_group_sizes_by_clause_type": peer_sizes,
            "fallbacks_used": sorted(set(all_fallbacks)),
        },
    }

    try:
        validated = BenchmarkAnalyzeResponse.model_validate(response_payload)
        return validated.model_dump()
    except ValidationError as exc:
        raise ValueError(f"Benchmark output schema validation failed: {exc}") from exc
