import html
import os
from datetime import datetime
from typing import Any
import requests
import streamlit as st
from frontend.styles.global_css import APP_CSS

st.set_page_config(page_title="Contract Intelligence", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
FRONTEND_BUILD = "streamlit-clean-rebuild-v1"


def init_state():
    defaults = {"token": None, "user": None, "page": "Home", "auth_mode": "login", "selected_contract_id": None, "last_analysis": None, "last_analysis_contract_id": None, "last_analysis_at": None, "analysis_result": None, "analysis_contract_label": None, "analysis_contract_id": None, "analysis_endpoint": None, "last_api_debug": None, "chat_history": [], "chat_contract_id": None, "chat_contract_label": None, "last_chat_debug": None, "benchmark_result": None, "benchmark_contract_id": None}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def parse_response_body(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def api_request(method: str, path: str, **kwargs) -> tuple[bool, Any]:
    headers = kwargs.pop("headers", {})
    timeout = kwargs.pop("timeout", 90)
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    url = f"{API_BASE_URL}{path}"
    debug = {"method": method.upper(), "base_url": API_BASE_URL, "path": path, "url": url, "status_code": None, "response_body": None, "error": None}
    try:
        response = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
        body = parse_response_body(response)
        debug["status_code"] = response.status_code
        debug["response_body"] = body
        st.session_state.last_api_debug = debug
        if response.status_code == 401:
            st.session_state.token = None
            st.session_state.user = None
            return False, {"message": "Session expired. Please sign in again.", **debug}
        if response.status_code == 404:
            return False, {"message": "Analysis endpoint not found." if "/analyze" in path else "Requested resource was not found.", **debug}
        if response.status_code == 422:
            return False, {"message": "Invalid contract id or request payload.", **debug}
        if response.status_code >= 500:
            detail = body.get("detail") if isinstance(body, dict) else body
            return False, {"message": safe_text(detail, "Backend returned an internal error."), **debug}
        if response.status_code >= 400:
            detail = body.get("detail") if isinstance(body, dict) else body
            return False, {"message": safe_text(detail, "Request failed."), **debug}
        return True, body
    except requests.ConnectionError as exc:
        debug["error"] = str(exc)
        st.session_state.last_api_debug = debug
        return False, {"message": "Backend connection failed.", **debug}
    except requests.Timeout as exc:
        debug["error"] = str(exc)
        st.session_state.last_api_debug = debug
        return False, {"message": "Backend request timed out before analysis completed.", **debug}
    except requests.RequestException as exc:
        debug["error"] = str(exc)
        st.session_state.last_api_debug = debug
        return False, {"message": "Backend request failed.", **debug}


def health_marker():
    try:
        r = requests.get(f"{API_BASE_URL}/healthz", timeout=3)
        return r.json() if r.ok else {"Backend Build": "unreachable"}
    except requests.RequestException:
        return {"Backend Build": "unreachable"}


def user_message(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        detail = value.get("message") or value.get("detail") or value.get("error")
        if isinstance(detail, str):
            return detail
        if detail is not None:
            return str(detail)
        return "; ".join(f"{key}: {val}" for key, val in value.items()) or "Something went wrong."
    if isinstance(value, list):
        return "; ".join(user_message(item) for item in value) or "Something went wrong."
    return str(value) if value is not None else "Something went wrong."


def safe_text(value: Any, fallback: str = "Not specified") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def safe_html(value: Any, fallback: str = "Not specified") -> str:
    return html.escape(safe_text(value, fallback))


def titleize(value: Any) -> str:
    return safe_text(value).replace("_", " ").title()


def plain_value(value: Any, fallback: str = "Not specified") -> str:
    if value is None:
        return fallback
    if isinstance(value, dict):
        parts = []
        for key, val in value.items():
            parts.append(f"{titleize(key)}: {plain_value(val, fallback='')}")
        return "; ".join(part for part in parts if part) or fallback
    if isinstance(value, list):
        return "; ".join(plain_value(item, fallback="") for item in value if plain_value(item, fallback="")) or fallback
    return safe_text(value, fallback)


def normalize_action(item: Any, default_source: str = "AI / rule-based review") -> dict[str, str]:
    if isinstance(item, dict):
        return {
            "action": safe_text(item.get("action") or item.get("title") or item.get("recommendation"), "Review this item."),
            "rationale": plain_value(item.get("rationale") or item.get("why") or item.get("reason"), "This item may affect contract clarity or risk."),
            "related_clause": safe_text(item.get("related_clause") or item.get("clause"), "General"),
            "priority": safe_text(item.get("priority"), "Medium"),
            "source": safe_text(item.get("source"), default_source),
        }
    return {"action": safe_text(item, "Review this item."), "rationale": "Recommended review point from the current analysis.", "related_clause": "General", "priority": "Medium", "source": default_source}


def render_action_card(action: dict[str, str]) -> None:
    st.markdown(f'<div class="cip-action-card"><div class="cip-card-header"><h4>{safe_html(action["action"])}</h4><span class="{badge_class(action["priority"])}">{safe_html(action["priority"])}</span></div><p><strong>Why this matters:</strong> {safe_html(action["rationale"])}</p><p><strong>Related clause:</strong> {safe_html(action["related_clause"])}</p><p><strong>Source:</strong> {safe_html(action["source"])}</p></div>', unsafe_allow_html=True)


def render_overall_visual(analysis: dict[str, Any]) -> None:
    score = analysis.get("health_score")
    score_number = int(score) if isinstance(score, (int, float)) else 0
    risk = analysis.get("risk_level", "Not specified")
    summary = plain_value(analysis.get("ai_overall_assessment"), "No AI overall assessment was returned.")
    cols = st.columns([1, 2])
    with cols[0]:
        st.markdown(f'<div class="cip-radial"><div class="cip-radial-score">{score_number}</div><div class="cip-muted">Overall Health / 100</div></div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'<div class="cip-summary-card"><div class="cip-card-meta"><span class="{badge_class(risk)}">Risk Signal: {safe_html(risk)}</span><span>Overall Health: {score_number}/100</span></div><p>{safe_html(summary)}</p></div>', unsafe_allow_html=True)
        st.progress(max(0, min(100, score_number)) / 100)


def clause_summary(clause_type: str, status: str) -> str:
    if status == "missing":
        return "This expected protection was not found in the extracted contract text."
    summaries = {
        "termination": "This clause explains how the agreement can end and what notice or cause may be required.",
        "payment": "This clause defines commercial obligations such as fees, invoices, compensation, and payment timing.",
        "confidentiality": "This clause protects sensitive business, technical, or proprietary information.",
        "liability": "This clause allocates financial exposure, indemnity, damages, and responsibility if something goes wrong.",
        "intellectual_property": "This clause explains ownership or permitted use of intellectual property and work product.",
        "governing_law": "This clause identifies which jurisdiction's law governs interpretation of the agreement.",
        "dispute_resolution": "This clause explains how disputes are escalated, mediated, arbitrated, or litigated.",
        "renewal": "This clause explains whether and how the contract renews or expires.",
    }
    return summaries.get(clause_type, "This clause was identified from the extracted contract text and should be reviewed in context.")


def generic_recommendation(clause_type: str, status: str) -> str:
    label = titleize(clause_type)
    if status == "missing":
        return f"Generic recommendation: add a clear {label} clause tailored to this deal before signature."
    recommendations = {
        "termination": "Generic recommendation: confirm notice period, cure period, termination for cause, and survival language are complete.",
        "payment": "Generic recommendation: confirm amounts, due dates, late fees, taxes, invoice process, and disputed-payment rights.",
        "confidentiality": "Generic recommendation: confirm exclusions, permitted disclosures, duration, and return/destruction obligations.",
        "liability": "Generic recommendation: confirm liability caps, excluded damages, indemnities, and exceptions are commercially acceptable.",
        "intellectual_property": "Generic recommendation: confirm ownership, licenses, deliverables, and pre-existing IP rights are explicit.",
        "governing_law": "Generic recommendation: confirm governing law and venue are acceptable to the business.",
        "dispute_resolution": "Generic recommendation: confirm escalation, forum, timing, and interim relief rights are workable.",
        "renewal": "Generic recommendation: confirm renewal term, notice window, price changes, and opt-out rights are clear.",
    }
    return recommendations.get(clause_type, f"Generic recommendation: review the {label} clause for completeness and negotiation risk.")


def normalize_evidence(evidence: Any) -> list[dict[str, Any]]:
    if not evidence:
        return []
    items = evidence if isinstance(evidence, list) else [evidence]
    normalized = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text") or item.get("snippet") or item.get("source_text") or item.get("quote")
            normalized.append({
                "text": safe_text(text, "No direct evidence captured for this clause."),
                "page": item.get("page") or item.get("page_number"),
                "source": item.get("source") or item.get("source_type") or "extracted_text",
                "keyword": item.get("keyword") or item.get("match") or "",
                "location": item.get("location") or item.get("line") or item.get("paragraph"),
                "confidence": item.get("confidence"),
            })
        else:
            normalized.append({"text": safe_text(item, "No direct evidence captured for this clause."), "page": None, "source": "extracted_text", "keyword": "", "location": None, "confidence": None})
    return normalized


def normalize_clause(clause: Any, index: int) -> dict[str, Any]:
    if not isinstance(clause, dict):
        clause = {"title": f"Clause {index + 1}", "type": "unknown", "evidence": [clause], "found": True}
    clause_type = safe_text(clause.get("type") or clause.get("category") or clause.get("id"), "unknown").lower()
    title = safe_text(clause.get("title") or titleize(clause_type), f"Clause {index + 1}")
    evidence = normalize_evidence(clause.get("evidence") or clause.get("sources") or clause.get("source_text"))
    found = clause.get("found")
    status = clause.get("status")
    if not status:
        if found is False:
            status = "missing"
        elif evidence:
            status = "found"
        else:
            status = "partial"
    status = safe_text(status, "partial").lower()
    confidence = clause.get("confidence") or clause.get("confidence_score")
    if isinstance(confidence, (int, float)):
        confidence_label = f"{int(float(confidence) * 100) if float(confidence) <= 1 else int(float(confidence))}%"
    elif confidence:
        confidence_label = safe_text(confidence)
    elif status == "found":
        confidence_label = "High"
    elif status == "missing":
        confidence_label = "Not applicable"
    else:
        confidence_label = "Not specified"
    page = clause.get("page") or clause.get("page_number")
    if not page and evidence:
        page = evidence[0].get("page")
    location = clause.get("location") or clause.get("source_location")
    if not location:
        if page:
            location = f"Page {page}"
        else:
            location = "Extracted contract text"
    return {
        "id": safe_text(clause.get("id"), f"clause-{index}"),
        "title": title,
        "type": clause_type,
        "status": status,
        "confidence": confidence_label,
        "page": page,
        "location": location,
        "evidence": evidence,
        "summary": plain_value(clause.get("rule_based_summary") or clause.get("summary") or clause.get("explanation"), clause_summary(clause_type, status)),
        "simple_explanation": plain_value(clause.get("simple_explanation") or clause.get("ai_insight"), clause_summary(clause_type, status)),
        "what_to_check_next": plain_value(clause.get("what_to_check_next"), generic_recommendation(clause_type, status)),
        "risk": safe_text(clause.get("risk") or clause.get("risk_level"), "Not specified"),
        "recommendation": safe_text(clause.get("ai_recommendation") or clause.get("recommendation") or clause.get("suggested_improvement"), generic_recommendation(clause_type, status)),
        "ai_insight": safe_text(clause.get("ai_insight"), "No AI insight was returned for this clause."),
        "ai_risk_assessment": safe_text(clause.get("ai_risk_assessment"), "No AI risk assessment was returned for this clause."),
        "ai_recommendation": safe_text(clause.get("ai_recommendation"), "No AI recommendation was returned for this clause."),
        "negotiation_note": safe_text(clause.get("negotiation_note"), "No negotiation note was returned for this clause."),
        "review_priority": safe_text(clause.get("review_priority"), "Medium"),
    }


def normalize_risk(risk: Any, index: int) -> dict[str, str]:
    if not isinstance(risk, dict):
        return {"title": f"Risk {index + 1}", "severity": "medium", "explanation": safe_text(risk), "affected_clause": "Not specified", "recommendation": "Review this risk with counsel."}
    return {
        "title": safe_text(risk.get("title"), f"Risk {index + 1}"),
        "severity": safe_text(risk.get("severity"), "medium").lower(),
        "explanation": safe_text(risk.get("explanation") or risk.get("description"), "No explanation provided."),
        "affected_clause": safe_text(risk.get("affected_clause") or risk.get("clause"), "Not specified"),
        "recommendation": safe_text(risk.get("recommendation") or risk.get("suggested_mitigation"), "Review this risk with legal counsel."),
    }


def normalize_analysis_response(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    clauses = [normalize_clause(clause, idx) for idx, clause in enumerate(data.get("clauses") or [])]
    missing = data.get("missing_critical_clauses") or []
    missing_names = [safe_text(item) for item in missing]
    found_count = sum(1 for clause in clauses if clause["status"] == "found")
    source = data.get("source") or data.get("analysis_source") or data.get("scoring_source") or "rule_based"
    return {
        "raw": data,
        "health_score": data.get("health_score"),
        "risk_level": safe_text(data.get("risk_level"), "Not specified"),
        "source": safe_text(source, "rule_based"),
        "llm_used": bool(data.get("llm_used", False)),
        "degraded_mode": bool(data.get("degraded_mode", False)),
        "ai_status": safe_text(data.get("ai_status"), "LLM unavailable" if data.get("degraded_mode") else "Not specified"),
        "active_model": safe_text(data.get("active_model") or data.get("model"), "Not specified"),
        "confidence": safe_text(data.get("confidence"), "Low" if data.get("degraded_mode") else "Medium"),
        "executive_summary": safe_text(data.get("executive_summary") or data.get("summary"), "No executive summary returned."),
        "ai_overall_assessment": plain_value(data.get("ai_overall_assessment"), "No AI overall assessment was returned."),
        "key_strengths": [plain_value(item) for item in (data.get("key_strengths") or [])],
        "key_risks": [plain_value(item) for item in (data.get("key_risks") or [])],
        "clauses": clauses,
        "clauses_found": found_count,
        "missing_critical_clauses": missing_names,
        "risks": [normalize_risk(risk, idx) for idx, risk in enumerate(data.get("risks") or [])],
        "recommended_improvements": [normalize_action(item) for item in (data.get("recommended_actions") or data.get("recommended_improvements") or data.get("recommendations") or [])],
        "evidence_trace": data.get("evidence_trace") or [],
        "rule_based_result": data.get("rule_based_result"),
        "llm_request_status": data.get("llm_request_status"),
        "raw_llm_response": data.get("raw_llm_response"),
        "created_at": data.get("created_at"),
    }


def badge_class(value: str) -> str:
    normalized = safe_text(value, "neutral").lower()
    if normalized in {"found", "low", "strong"}:
        return "cip-badge cip-badge-green"
    if normalized in {"partial", "medium", "developing"}:
        return "cip-badge cip-badge-amber"
    if normalized in {"missing", "high", "critical", "weak"}:
        return "cip-badge cip-badge-red"
    return "cip-badge cip-badge-blue"


def render_metric_card(label: str, value: Any, detail: str = "") -> None:
    st.markdown(f'<div class="cip-kpi"><div class="cip-kpi-label">{safe_html(label)}</div><div class="cip-kpi-value">{safe_html(value)}</div><div class="cip-kpi-detail">{safe_html(detail, "")}</div></div>', unsafe_allow_html=True)


def render_score_cards(analysis: dict[str, Any]) -> None:
    cols = st.columns(5)
    score = analysis.get("health_score")
    score_value = f"{score}/100" if score is not None else "Not scored"
    mode = "Hybrid AI + rule-based" if analysis.get("llm_used") else "Rule-based fallback"
    with cols[0]:
        render_metric_card("AI Status", analysis["ai_status"], mode)
    with cols[1]:
        render_metric_card("Model", analysis["active_model"], f"Confidence: {analysis['confidence']}")
    with cols[2]:
        render_metric_card("Health Score", score_value, analysis["risk_level"])
    with cols[3]:
        render_metric_card("Clauses Found", analysis["clauses_found"], "Rule-based extraction")
    with cols[4]:
        render_metric_card("Missing Critical", len(analysis["missing_critical_clauses"]), analysis["source"])


def render_evidence(evidence: list[dict[str, Any]]) -> None:
    if not evidence:
        st.caption("No direct evidence captured for this clause.")
        return
    for idx, item in enumerate(evidence, start=1):
        page = item.get("page")
        location = item.get("location") or (f"Page {page}" if page else "Extracted contract text")
        source = item.get("source") or "extracted_text"
        confidence = item.get("confidence") or "Not specified"
        keyword = item.get("keyword") or "Not specified"
        st.markdown(f'<div class="cip-evidence"><div class="cip-evidence-meta">Evidence {idx} · Source: {safe_html(source)} · Location: {safe_html(location)} · Keyword: {safe_html(keyword)} · Confidence: {safe_html(confidence)}</div><blockquote>{safe_html(item.get("text"), "No direct evidence captured for this clause.")}</blockquote></div>', unsafe_allow_html=True)


def render_chat_evidence(evidence: list[dict[str, Any]]) -> None:
    if not evidence:
        st.caption("No contract evidence was used for this answer.")
        return
    for idx, item in enumerate(evidence, start=1):
        clause = item.get("clause") or "Relevant contract text"
        source = item.get("source") or "extracted_contract_text"
        location = item.get("location") or "Extracted contract text"
        text = item.get("text") or "No direct evidence captured."
        st.markdown(f'<div class="cip-evidence"><div class="cip-evidence-meta">Card {idx} · Clause: {safe_html(clause)} · Source: {safe_html(source)} · Location: {safe_html(location)}</div><blockquote>{safe_html(text)}</blockquote><div class="cip-muted">Why it matters: this is the contract text used to support the answer.</div></div>', unsafe_allow_html=True)


def confidence_human(confidence: Any, label: str | None = None) -> str:
    if label:
        return label
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return "Medium — this answer should be confirmed against the contract."
    if value >= 0.8:
        return "High — the contract clearly mentions this."
    if value >= 0.5:
        return "Medium — the contract partly answers this, but some details should be confirmed."
    return "Low — the contract does not clearly answer this."


def render_assistant_message(message: dict[str, Any]) -> None:
    st.markdown(f'<div class="cip-assistant-bubble"><div class="cip-eyebrow">Contract Assistant · {safe_html(message.get("answer_type"), "conversation")}</div><p>{safe_html(message.get("content"), "")}</p><p><strong>Plain-English summary:</strong> {safe_html(message.get("plain_english_summary"), "No summary returned.")}</p><p><strong>Practical note:</strong> {safe_html(message.get("practical_note"), "No practical note returned.")}</p><div class="cip-card-meta"><span>{safe_html(confidence_human(message.get("confidence"), message.get("confidence_label")))}</span><span>Used contract: {safe_html(message.get("used_contract"))}</span><span>LLM used: {safe_html(message.get("llm_used"))}</span></div></div>', unsafe_allow_html=True)
    with st.expander("Evidence used", expanded=False):
        render_chat_evidence(message.get("evidence") or [])
    suggestions = message.get("follow_up_suggestions") or []
    if suggestions:
        st.markdown("**Suggested follow-ups**")
        st.markdown(" ".join(f'<span class="cip-suggestion-chip">{safe_html(item)}</span>' for item in suggestions[:4]), unsafe_allow_html=True)


def append_chat_message(role: str, content: str, **metadata: Any) -> None:
    item = {"role": role, "content": content, "timestamp": datetime.now().strftime("%H:%M:%S")}
    item.update(metadata)
    st.session_state.chat_history.append(item)


def render_clause_card(clause: dict[str, Any]) -> None:
    status_class = badge_class(clause["status"])
    priority_class = badge_class(clause["review_priority"])
    st.markdown(f'<div class="cip-review-card"><div class="cip-card-header"><div><div class="cip-eyebrow">AI Review by Clause</div><h3>{safe_html(clause["title"])}</h3></div><span class="{status_class}">{safe_html(clause["status"].title())}</span></div><div class="cip-card-meta"><span>Type: {safe_html(clause["type"])}</span><span>Rule confidence: {safe_html(clause["confidence"])}</span><span>Source: {safe_html(clause["location"])}</span><span class="{priority_class}">Priority: {safe_html(clause["review_priority"])}</span></div><p><strong>Rule-based detection:</strong> {safe_html(clause["summary"])}</p></div>', unsafe_allow_html=True)
    st.markdown("**Evidence from contract**")
    render_evidence(clause["evidence"])
    st.markdown(f'<div class="cip-ai-box"><strong>Simple explanation:</strong><br>{safe_html(clause["simple_explanation"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-ai-box"><strong>Why it matters:</strong><br>{safe_html(clause["ai_insight"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-ai-box"><strong>Risk in plain English:</strong><br>{safe_html(clause["ai_risk_assessment"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-recommendation"><strong>What to check next:</strong> {safe_html(clause["what_to_check_next"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-recommendation"><strong>AI recommendation:</strong> {safe_html(clause["ai_recommendation"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-negotiation"><strong>Negotiation note:</strong> {safe_html(clause["negotiation_note"])}</div>', unsafe_allow_html=True)


def render_risk_card(risk: dict[str, str]) -> None:
    st.markdown(f'<div class="cip-risk-card"><div class="cip-card-header"><h4>{safe_html(risk["title"])}</h4><span class="{badge_class(risk["severity"])}">{safe_html(risk["severity"].title())}</span></div><p>{safe_html(risk["explanation"])}</p><p><strong>Affected clause:</strong> {safe_html(risk["affected_clause"])}</p><p><strong>Recommendation:</strong> {safe_html(risk["recommendation"])}</p></div>', unsafe_allow_html=True)


def render_missing_clause_card(name: str) -> None:
    label = titleize(name)
    st.markdown(f'<div class="cip-missing-card"><div class="cip-card-header"><h4>{safe_html(label)}</h4><span class="cip-badge cip-badge-red">High Priority</span></div><p><strong>Why it matters:</strong> {safe_html(clause_summary(safe_text(name).lower(), "missing"))}</p><p><strong>Suggested wording direction:</strong> {safe_html(generic_recommendation(safe_text(name).lower(), "missing"))}</p></div>', unsafe_allow_html=True)


def render_recommendations(analysis: dict[str, Any]) -> None:
    recommendations = list(analysis.get("recommended_improvements") or [])
    for missing in analysis.get("missing_critical_clauses") or []:
        recommendations.append(normalize_action({"action": generic_recommendation(missing, "missing"), "rationale": "A critical clause was not detected in the extracted text.", "related_clause": titleize(missing), "priority": "High", "source": "rule-based missing clause"}))
    if analysis.get("risks"):
        recommendations.append(normalize_action({"action": "Review high-risk terms with legal counsel before signature.", "rationale": "The risk summary includes one or more review signals.", "related_clause": "Risk summary", "priority": "High", "source": "AI / rule-based review"}))
    if not recommendations:
        recommendations.append(normalize_action("No major remediation actions were identified. Confirm business terms and final legal review before signature."))
    for item in recommendations:
        render_action_card(normalize_action(item))


def normalize_benchmark_response(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    comparisons = data.get("clause_alignment") or []
    actions = [normalize_action(item, "illustrative benchmark comparison") for item in (data.get("recommended_improvements") or [])]
    return {
        "raw": data,
        "benchmark_mode": safe_text(data.get("benchmark_mode"), "Illustrative benchmark comparison"),
        "profiles": data.get("benchmark_profiles") or [],
        "overall_score": data.get("overall_score", 0),
        "aligned": data.get("aligned_clauses", 0),
        "partial": data.get("partially_aligned_clauses", 0),
        "missing": data.get("missing_or_weak_clauses", len(data.get("missing_protections") or [])),
        "market_position": safe_text(data.get("market_position"), "Not specified"),
        "narrative_summary": plain_value(data.get("narrative_summary"), "This comparison uses internal illustrative benchmark profiles to compare common contract structures."),
        "comparisons": comparisons,
        "actions": actions,
    }


def render_benchmark_results(result: dict[str, Any]) -> None:
    cols = st.columns(5)
    with cols[0]:
        render_metric_card("Overall Benchmark Score", f"{result['overall_score']}/100", result["market_position"])
    with cols[1]:
        render_metric_card("Aligned Clauses", result["aligned"], "Strong alignment")
    with cols[2]:
        render_metric_card("Partially Aligned", result["partial"], "Needs review")
    with cols[3]:
        render_metric_card("Missing / Weak", result["missing"], "Priority gaps")
    with cols[4]:
        render_metric_card("Benchmark Mode", "Illustrative", "Synthetic profiles")
    st.info("This comparison uses internal illustrative benchmark profiles to show how the selected contract compares against common contract structures. It is not live market data.")
    st.markdown(f'<div class="cip-summary-card"><strong>Benchmark narrative</strong><br>{safe_html(result["narrative_summary"])}</div>', unsafe_allow_html=True)
    st.markdown("### Alignment Snapshot")
    total = max(1, result["aligned"] + result["partial"] + result["missing"])
    for label, value in [("Strong alignment", result["aligned"]), ("Moderate alignment", result["partial"]), ("Missing / weak", result["missing"])]:
        pct = int(value / total * 100)
        st.markdown(f'<div><strong>{safe_html(label)}</strong> — {value} clauses<div class="cip-mini-bar"><span style="width:{pct}%"></span></div></div>', unsafe_allow_html=True)
    st.markdown("### Clause-by-Clause Comparison")
    for item in result["comparisons"]:
        status = safe_text(item.get("your_contract_status"), "Not specified")
        st.markdown(f'<div class="cip-benchmark-card"><div class="cip-card-header"><h4>{safe_html(item.get("clause"))}</h4><span class="{badge_class(status)}">{safe_html(status)}</span></div><p><strong>Your contract:</strong> {safe_html(status)}</p><p><strong>Benchmark expectation:</strong> {safe_html(item.get("benchmark_expectation"))}</p><p><strong>Gap assessment:</strong> {safe_html(item.get("gap_assessment"))}</p><p><strong>Plain-English explanation:</strong> {safe_html(item.get("plain_english_explanation"))}</p><p><strong>Suggested improvement:</strong> {safe_html(item.get("improvement_suggestion"))}</p></div>', unsafe_allow_html=True)
    st.markdown("### Benchmark Recommended Actions")
    if result["actions"]:
        for action in result["actions"]:
            render_action_card(action)
    else:
        st.success("No major benchmark gaps were identified against the illustrative profiles.")
    with st.expander("Advanced / Debug Output", expanded=False):
        st.caption("Raw benchmark response for debugging only")
        st.json(result["raw"])


def render_analysis_results(analysis: dict[str, Any]) -> None:
    render_score_cards(analysis)
    st.markdown("### AI Executive Review")
    render_overall_visual(analysis)
    st.markdown(f'<div class="cip-summary-card"><strong>Executive summary</strong><br>{safe_html(analysis["executive_summary"])}</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]:
        st.markdown("**Key strengths**")
        for item in analysis["key_strengths"] or ["No AI-identified strengths returned."]:
            st.markdown(f'<div class="cip-check-item">✓ {safe_html(item)}</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown("**Key risks**")
        for item in analysis["key_risks"] or ["No AI-identified risks returned."]:
            st.markdown(f'<div class="cip-risk-chip">⚠ {safe_html(item)}</div>', unsafe_allow_html=True)
    with cols[2]:
        st.markdown("**Recommended next actions**")
        for item in analysis["recommended_improvements"] or [normalize_action("No AI recommendations returned.")]:
            action = normalize_action(item)
            st.markdown(f'<div class="cip-check-item">→ {safe_html(action["action"])}</div>', unsafe_allow_html=True)

    st.markdown("### Risk Summary")
    if analysis["risks"]:
        for risk in analysis["risks"]:
            render_risk_card(risk)
    else:
        st.info("No major risks detected based on the extracted clauses.")

    st.markdown("### AI Review by Clause")
    if analysis["clauses"]:
        for clause in analysis["clauses"]:
            render_clause_card(clause)
    else:
        st.warning("No clauses were extracted from this contract yet.")

    st.markdown("### Missing Critical Clauses")
    if analysis["missing_critical_clauses"]:
        for missing in analysis["missing_critical_clauses"]:
            render_missing_clause_card(missing)
    else:
        st.success("No missing critical clauses were detected by the rule-based review.")

    st.markdown("### Recommended Actions")
    render_recommendations(analysis)

    st.markdown("### Evidence Trace")
    has_evidence = False
    for clause in analysis["clauses"]:
        st.markdown(f'<div class="cip-evidence"><div class="cip-evidence-meta">Clause: {safe_html(clause["title"])} · Confidence: {safe_html(clause["confidence"])}</div></div>', unsafe_allow_html=True)
        render_evidence(clause["evidence"])
        has_evidence = True
    if not has_evidence:
        st.caption("No evidence trace is available yet.")

    with st.expander("Advanced / Debug Output", expanded=False):
        st.caption("Rule-based result")
        st.json(analysis.get("rule_based_result") or {})
        st.caption("LLM request status")
        st.json(analysis.get("llm_request_status") or {})
        st.caption("Parsed AI output")
        st.json(analysis.get("raw_llm_response") or {})
        st.caption("Raw backend response for debugging only")
        st.json(analysis["raw"])


def render_sidebar():
    health = health_marker()
    st.sidebar.markdown("### Contract Intelligence")
    st.sidebar.caption("Active Frontend: Streamlit")
    st.sidebar.caption("Active Frontend File: frontend/streamlit_app.py")
    st.sidebar.caption(f"Frontend Build: {FRONTEND_BUILD}")
    st.sidebar.caption(f"Backend Build: {health.get('Backend Build', 'unknown')}")
    if st.session_state.user:
        st.sidebar.divider()
        st.sidebar.caption("Signed in as")
        st.sidebar.write(st.session_state.user.get("email"))
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()
        st.sidebar.divider()
        pages = ["Home", "Clients", "Contracts", "Contract Analysis", "Contract Chat", "Benchmark", "Settings / System Health"]
        st.session_state.page = st.sidebar.radio("Navigate", pages, index=pages.index(st.session_state.page) if st.session_state.page in pages else 0)


def auth_screen():
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown('<div class="cip-hero"><span class="cip-pill">Contract Intelligence</span><h1>Review contracts with evidence, risk, and clarity.</h1><p class="cip-muted">Secure Streamlit MVP backed by FastAPI, MongoDB, and grounded rule-based analysis.</p></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.05, 1])
    with col2:
        st.write("")
        mode = st.radio("Account action", ["Sign In", "Create Account"], horizontal=True, label_visibility="collapsed")
        st.session_state.auth_mode = "register" if mode == "Create Account" else "login"
        st.markdown('<div class="cip-auth-card">', unsafe_allow_html=True)
        with st.container():
            if st.session_state.auth_mode == "register":
                st.header("Create account")
                with st.form("register_form"):
                    full_name = st.text_input("Full name", autocomplete="name")
                    email = st.text_input("Email", autocomplete="email")
                    password = st.text_input("Password", type="password", autocomplete="new-password")
                    confirm = st.text_input("Confirm password", type="password", autocomplete="new-password")
                    submitted = st.form_submit_button("Create account", use_container_width=True)
                if submitted:
                    if len(full_name.strip()) < 2:
                        st.error("Enter your full name.")
                    elif "@" not in email:
                        st.error("Enter a valid email address.")
                    elif len(password) < 8:
                        st.error("Password must be at least 8 characters.")
                    elif password != confirm:
                        st.error("Passwords do not match.")
                    else:
                        with st.spinner("Creating account..."):
                            ok, data = api_request("POST", "/auth/register", json={"full_name": full_name, "email": email, "password": password})
                        if ok:
                            st.success("Account created. Please sign in.")
                            st.session_state.auth_mode = "login"
                        else:
                            st.error(user_message(data))
            else:
                st.header("Log in")
                with st.form("login_form"):
                    email = st.text_input("Email", autocomplete="email")
                    password = st.text_input("Password", type="password", autocomplete="current-password")
                    submitted = st.form_submit_button("Log in", use_container_width=True)
                if submitted:
                    if not email or not password:
                        st.error("Email and password are required.")
                    else:
                        with st.spinner("Signing in..."):
                            ok, data = api_request("POST", "/auth/login", json={"email": email, "password": password})
                        if ok:
                            st.session_state.token = data["access_token"]
                            st.session_state.user = data["user"]
                            st.rerun()
                        else:
                            st.error(user_message(data))
        st.markdown('</div>', unsafe_allow_html=True)


def require_auth():
    if not st.session_state.token:
        return False
    ok, data = api_request("GET", "/auth/me")
    if ok:
        st.session_state.user = data
        return True
    st.warning(user_message(data))
    return False


def home():
    st.title("Home Dashboard")
    ok_c, clients = api_request("GET", "/clients")
    ok_k, contracts = api_request("GET", "/contracts")
    c1,c2,c3 = st.columns(3)
    c1.metric("Clients", len(clients) if ok_c else 0)
    c2.metric("Contracts", len(contracts) if ok_k else 0)
    c3.metric("Review status", "Ready")
    st.info("Start by creating a client, uploading a contract, then running analysis, chat, and benchmark workflows.")


def clients_page():
    st.title("Clients")
    with st.form("client_form", clear_on_submit=True):
        name = st.text_input("Client name")
        industry = st.text_input("Industry")
        notes = st.text_area("Notes")
        if st.form_submit_button("Create client"):
            ok, data = api_request("POST", "/clients", json={"name": name, "industry": industry, "notes": notes})
            if ok:
                st.success("Client created.")
            else:
                st.error(user_message(data))
    ok, data = api_request("GET", "/clients")
    if ok and data:
        st.dataframe(data, use_container_width=True)
    else:
        st.caption("No clients yet.")


def contracts_page():
    st.title("Contracts")
    ok, clients = api_request("GET", "/clients")
    client_options = {c["name"]: c["id"] for c in clients} if ok else {}
    with st.form("upload_form"):
        name = st.text_input("Contract name")
        client_name = st.selectbox("Client", ["No client"] + list(client_options.keys()))
        file = st.file_uploader("Upload PDF, DOCX, or TXT", type=["pdf", "docx", "txt"])
        if st.form_submit_button("Upload contract"):
            if not file:
                st.error("Choose a contract file.")
            else:
                files = {"file": (file.name, file.getvalue())}
                data = {"name": name or file.name}
                if client_name != "No client":
                    data["client_id"] = client_options[client_name]
                ok, resp = api_request("POST", "/contracts/upload", files=files, data=data)
                if ok:
                    st.success("Contract uploaded.")
                else:
                    st.error(user_message(resp))
    ok, contracts = api_request("GET", "/contracts")
    if ok and contracts:
        st.dataframe([{k:v for k,v in c.items() if k != "extracted_text"} for c in contracts], use_container_width=True)
    else:
        st.caption("No contracts uploaded yet.")


def select_contract():
    ok, contracts = api_request("GET", "/contracts")
    if not ok or not contracts:
        st.warning("Upload a contract first.")
        return None, None
    label_to_contract_id = {}
    for contract in contracts:
        contract_id = contract.get("id") or contract.get("_id")
        if not contract_id:
            continue
        name = contract.get("name") or contract.get("filename") or "Untitled contract"
        label = f"{name} ({str(contract_id)[:6]})"
        label_to_contract_id[label] = str(contract_id)
    if not label_to_contract_id:
        st.warning("No valid contract ids were returned by the backend.")
        return None, None
    selected_label = st.selectbox("Contract", list(label_to_contract_id.keys()))
    return selected_label, label_to_contract_id[selected_label]


def analysis_page():
    st.title("Contract Analysis")
    st.caption("Review extracted clauses, risks, evidence, and recommended actions.")
    selected_label, cid = select_contract()
    if not cid:
        return
    endpoint_path = f"/contracts/{cid}/analyze"
    st.session_state.analysis_contract_label = selected_label
    st.session_state.analysis_contract_id = cid
    st.session_state.analysis_endpoint = endpoint_path
    if st.session_state.get("last_analysis_contract_id") == cid and st.session_state.get("last_analysis_at"):
        st.caption(f"Last analyzed: {st.session_state.last_analysis_at}")
    if st.button("Run Analysis", use_container_width=True):
        with st.spinner("Analyzing contract and extracting evidence..."):
            ok, data = api_request("POST", endpoint_path, timeout=120)
        if ok:
            normalized = normalize_analysis_response(data)
            st.session_state.last_analysis = normalized
            st.session_state.analysis_result = normalized
            st.session_state.last_analysis_contract_id = cid
            st.session_state.last_analysis_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.success("Analysis complete.")
        else:
            st.markdown(f'<div class="cip-error-card"><strong>Analysis failed.</strong><br>{safe_html(user_message(data))}</div>', unsafe_allow_html=True)
            return
    with st.expander("Advanced / API Debug", expanded=False):
        latest_debug = st.session_state.last_api_debug or {}
        st.write({
            "backend_base_url": API_BASE_URL,
            "selected_contract_label": selected_label,
            "selected_contract_id": cid,
            "endpoint_path": endpoint_path,
            "http_method": "POST",
            "status_code": latest_debug.get("status_code"),
            "response_body": latest_debug.get("response_body"),
            "error": latest_debug.get("error"),
        })
    if st.session_state.get("last_analysis_contract_id") == cid and st.session_state.get("analysis_result"):
        render_analysis_results(st.session_state.analysis_result)
    else:
        st.info("Run analysis to see health score, risks, clauses, recommendations, and evidence trace.")


def chat_page():
    st.title("Contract Chat")
    st.caption("Ask questions about this contract, risks, clauses, obligations, or general follow-up questions.")
    selected_label, cid = select_contract()
    if not cid:
        return
    if st.session_state.chat_contract_id and st.session_state.chat_contract_id != cid:
        st.warning("You selected a different contract. Start a new chat to avoid mixing evidence between contracts.")
        if st.button("New chat for selected contract", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.chat_contract_id = cid
            st.session_state.chat_contract_label = selected_label
            st.rerun()
        return
    if not st.session_state.chat_contract_id:
        st.session_state.chat_contract_id = cid
        st.session_state.chat_contract_label = selected_label
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown(f'<div class="cip-chat-contract">Selected contract: <strong>{safe_html(selected_label)}</strong></div>', unsafe_allow_html=True)
    with cols[1]:
        if st.button("New chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.chat_contract_id = cid
            st.session_state.chat_contract_label = selected_label
            st.rerun()
    if not st.session_state.chat_history:
        st.markdown(" ".join(f'<span class="cip-suggestion-chip">{safe_html(item)}</span>' for item in ["What are my key obligations?", "What risks should I review first?", "Explain this in simple terms", "What should I negotiate?"]), unsafe_allow_html=True)
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(safe_html(message["content"]))
        else:
            with st.chat_message("assistant"):
                render_assistant_message(message)
    prompt = st.chat_input("Ask about the selected contract, or ask a general follow-up question...")
    if prompt:
        append_chat_message("user", prompt)
        endpoint_path = f"/contracts/{cid}/chat"
        with st.spinner("Thinking through the contract context..."):
            ok, data = api_request("POST", endpoint_path, json={"question": prompt}, timeout=120)
        if ok:
            append_chat_message(
                "assistant",
                data.get("answer", "I could not generate an answer."),
                answer_type=data.get("answer_type"),
                confidence=data.get("confidence"),
                confidence_label=data.get("confidence_label"),
                used_contract=data.get("used_contract"),
                evidence=data.get("evidence") or [],
                plain_english_summary=data.get("plain_english_summary"),
                practical_note=data.get("practical_note"),
                follow_up_suggestions=data.get("follow_up_suggestions") or [],
                degraded_mode=data.get("degraded_mode"),
                llm_used=data.get("llm_used"),
                raw=data,
            )
            st.rerun()
        else:
            st.markdown(f'<div class="cip-error-card"><strong>I could not complete the chat request.</strong><br>{safe_html(user_message(data))}</div>', unsafe_allow_html=True)
    with st.expander("Advanced / Debug Output", expanded=False):
        st.caption("Last chat/API debug details")
        st.json({"contract_id": cid, "contract_label": selected_label, "last_api_debug": st.session_state.last_api_debug, "last_assistant_raw": next((m.get("raw") for m in reversed(st.session_state.chat_history) if m.get("role") == "assistant"), None)})


def benchmark_page():
    st.title("Benchmark")
    st.caption("Compare the selected contract against clearly labeled synthetic benchmark profiles.")
    selected_label, cid = select_contract()
    if not cid:
        return
    st.markdown(f'<div class="cip-chat-contract">Selected contract: <strong>{safe_html(selected_label)}</strong></div>', unsafe_allow_html=True)
    if st.button("Run benchmark", use_container_width=True):
        with st.spinner("Comparing against illustrative benchmark profiles..."):
            ok, data = api_request("POST", f"/contracts/{cid}/benchmark", timeout=90)
        if ok:
            st.session_state.benchmark_result = normalize_benchmark_response(data)
            st.session_state.benchmark_contract_id = cid
            st.success("Benchmark comparison complete.")
        else:
            st.markdown(f'<div class="cip-error-card"><strong>Benchmark failed.</strong><br>{safe_html(user_message(data))}</div>', unsafe_allow_html=True)
            return
    if st.session_state.get("benchmark_contract_id") == cid and st.session_state.get("benchmark_result"):
        render_benchmark_results(st.session_state.benchmark_result)
    else:
        st.info("Run benchmark to compare this contract against illustrative benchmark profiles.")


def settings_page():
    st.title("Settings / System Health")
    health = health_marker()
    cols = st.columns(4)
    with cols[0]:
        render_metric_card("Frontend Build", FRONTEND_BUILD, "Streamlit")
    with cols[1]:
        render_metric_card("Backend Build", health.get("Backend Build", "unknown"), health.get("Active Backend", "FastAPI"))
    with cols[2]:
        render_metric_card("LLM Reachable", health.get("llm_reachable", "unknown"), health.get("llm_ollama_status", "unknown"))
    with cols[3]:
        render_metric_card("Active Model", health.get("active_model", "unknown"), "Ollama")
    st.markdown("### LLM / Ollama")
    st.write({"Ollama URL": health.get("ollama_url"), "Active model": health.get("active_model"), "Reachable": health.get("llm_reachable"), "Last LLM error": health.get("last_llm_error")})
    with st.expander("Raw health response", expanded=False):
        st.json(health)
    st.caption(f"API Base URL: {API_BASE_URL}")


def main():
    init_state()
    render_sidebar()
    if not require_auth():
        auth_screen()
        return
    st.markdown(APP_CSS, unsafe_allow_html=True)
    {"Home": home, "Clients": clients_page, "Contracts": contracts_page, "Contract Analysis": analysis_page, "Contract Chat": chat_page, "Benchmark": benchmark_page, "Settings / System Health": settings_page}[st.session_state.page]()

if __name__ == "__main__":
    main()
