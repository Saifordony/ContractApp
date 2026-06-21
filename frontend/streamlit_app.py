import html
import os
from datetime import datetime
from typing import Any
import requests
import streamlit as st
from frontend.styles.global_css import build_app_css

st.set_page_config(page_title="Contract Intelligence", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
FRONTEND_BUILD = "streamlit-clean-rebuild-v1"


TRANSLATIONS = {
    "en": {
        "app.name": "Contract Intelligence",
        "app.subtitle": "AI-powered contract review workspace",
        "nav.dashboard": "Dashboard",
        "nav.workspace": "Workspace",
        "nav.system": "System",
        "page.Home.title": "Home Dashboard",
        "page.Home.subtitle": "Track clients, contracts, reviews, and next actions from one workspace.",
        "page.Clients.title": "Clients",
        "page.Clients.subtitle": "Create and manage client records used to organize contracts.",
        "page.Contracts.title": "Contracts",
        "page.Contracts.subtitle": "Upload, browse, and organize contract files for review.",
        "page.Contract Analysis.title": "Contract Analysis",
        "page.Contract Analysis.subtitle": "Review extracted clauses, risks, evidence, and recommended actions.",
        "page.Contract Chat.title": "Contract Chat",
        "page.Contract Chat.subtitle": "Ask questions about this contract, risks, clauses, obligations, or general follow-up questions.",
        "page.Benchmark.title": "Benchmark",
        "page.Benchmark.subtitle": "Compare the selected contract against internal checklist templates, not live market data.",
        "page.Settings / System Health.title": "Settings / System Health",
        "page.Settings / System Health.subtitle": "Diagnostics for frontend, backend, database, authentication, AI model, endpoints, and runtime configuration.",
        "action.logout": "Logout",
        "action.create_client": "Create client",
        "action.upload_contract": "Upload contract",
        "action.run_analysis": "Run Analysis",
        "action.new_chat": "New chat",
        "action.run_benchmark": "Run benchmark",
        "theme.light": "Light",
        "theme.dark": "Dark",
        "language.english": "English",
        "language.arabic": "العربية",
        "status.healthy": "Healthy",
        "status.degraded": "Degraded",
        "status.offline": "Offline",
        "empty.clients": "No clients yet. Create your first client to start organizing contracts.",
        "empty.contracts": "No contracts uploaded yet. Upload a contract to begin analysis.",
        "home.help": "Start by creating a client, uploading a contract, then running analysis, chat, and benchmark workflows.",
        "label.signed_in_as": "Signed in as",
        "label.theme": "Theme",
        "label.language": "Language",
        "label.ai_explanation_language": "AI Explanation Language",
        "label.report_language": "Report Language",
        "label.frontend_build": "Frontend Build",
        "label.backend_build": "Backend Build",
        "label.active_frontend": "Active Frontend: Streamlit",
        "label.active_file": "Active Frontend File: frontend/streamlit_app.py",
    },
    "ar": {
        "app.name": "ذكاء العقود",
        "app.subtitle": "مساحة عمل لمراجعة العقود بالذكاء الاصطناعي",
        "nav.dashboard": "لوحة التحكم",
        "nav.workspace": "مساحة العمل",
        "nav.system": "النظام",
        "page.Home.title": "لوحة التحكم الرئيسية",
        "page.Home.subtitle": "تابع العملاء والعقود والمراجعات والإجراءات التالية من مساحة واحدة.",
        "page.Clients.title": "العملاء",
        "page.Clients.subtitle": "أنشئ وأدر سجلات العملاء لتنظيم العقود.",
        "page.Contracts.title": "العقود",
        "page.Contracts.subtitle": "ارفع وتصفح ونظم ملفات العقود للمراجعة.",
        "page.Contract Analysis.title": "تحليل العقد",
        "page.Contract Analysis.subtitle": "راجع البنود والمخاطر والأدلة والإجراءات المقترحة.",
        "page.Contract Chat.title": "محادثة العقد",
        "page.Contract Chat.subtitle": "اطرح أسئلة عن العقد والمخاطر والبنود والالتزامات أو أسئلة متابعة عامة.",
        "page.Benchmark.title": "المقارنة المرجعية",
        "page.Benchmark.subtitle": "قارن العقد المحدد بملفات مرجعية توضيحية مصنفة بوضوح.",
        "page.Settings / System Health.title": "الإعدادات / صحة النظام",
        "page.Settings / System Health.subtitle": "تشخيص الواجهة والخادم وقاعدة البيانات والمصادقة ونموذج الذكاء الاصطناعي ونقاط النهاية.",
        "action.logout": "تسجيل الخروج",
        "action.create_client": "إنشاء عميل",
        "action.upload_contract": "رفع عقد",
        "action.run_analysis": "تشغيل التحليل",
        "action.new_chat": "محادثة جديدة",
        "action.run_benchmark": "تشغيل المقارنة",
        "theme.light": "فاتح",
        "theme.dark": "داكن",
        "language.english": "English",
        "language.arabic": "العربية",
        "status.healthy": "سليم",
        "status.degraded": "متدهور",
        "status.offline": "غير متصل",
        "empty.clients": "لا يوجد عملاء بعد. أنشئ أول عميل لبدء تنظيم العقود.",
        "empty.contracts": "لا توجد عقود مرفوعة بعد. ارفع عقداً لبدء التحليل.",
        "home.help": "ابدأ بإنشاء عميل ورفع عقد ثم تشغيل التحليل والمحادثة والمقارنة المرجعية.",
        "label.signed_in_as": "تم تسجيل الدخول باسم",
        "label.theme": "السمة",
        "label.language": "اللغة",
        "label.ai_explanation_language": "لغة الشرح بالذكاء الاصطناعي",
        "label.report_language": "لغة التقرير",
        "label.frontend_build": "إصدار الواجهة",
        "label.backend_build": "إصدار الخادم",
        "label.active_frontend": "الواجهة النشطة: Streamlit",
        "label.active_file": "ملف الواجهة النشط: frontend/streamlit_app.py",
    },
}

NAV_GROUPS = [
    ("nav.dashboard", [("Home", "🏠")]),
    ("nav.workspace", [("Clients", "🏢"), ("Contracts", "📄"), ("Contract Analysis", "🔎"), ("Contract Chat", "💬"), ("Benchmark", "📊")]),
    ("nav.system", [("Settings / System Health", "⚙️")]),
]

QUICK_ACTIONS = {
    "Clients": "action.create_client",
    "Contracts": "action.upload_contract",
    "Contract Analysis": "action.run_analysis",
    "Contract Chat": "action.new_chat",
    "Benchmark": "action.run_benchmark",
}


def t(key: str, fallback: str | None = None) -> str:
    lang = st.session_state.get("language", "en")
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, fallback or key))


def is_rtl() -> bool:
    return st.session_state.get("language") == "ar"


def effective_explanation_language() -> str:
    pref = st.session_state.get("ai_explanation_language", "match")
    return st.session_state.get("language", "en") if pref == "match" else pref


def effective_report_language() -> str:
    pref = st.session_state.get("report_language", "match")
    return st.session_state.get("language", "en") if pref == "match" else pref


def localized_label(en: str, ar: str) -> str:
    return ar if effective_explanation_language() == "ar" else en


def localized_label_for(lang: str | None, en: str, ar: str) -> str:
    return ar if lang == "ar" else en


def localized_status(value: str) -> str:
    mapping = {"Healthy": "status.healthy", "Degraded": "status.degraded", "Offline": "status.offline"}
    return t(mapping.get(value, value), value)


def current_lang() -> str:
    return st.session_state.get("language", "en")


def format_bool(value: Any, lang: str | None = None) -> str:
    lang = lang or current_lang()
    truthy = value is True or str(value).lower() in {"true", "yes", "1", "enabled", "connected"}
    return ("نعم" if truthy else "لا") if lang == "ar" else ("Yes" if truthy else "No")


def format_clause_type(value: Any, lang: str | None = None) -> str:
    lang = lang or current_lang()
    key = safe_text(value, "").lower().replace(" ", "_").replace("/", "_")
    en = {"termination":"Termination", "payment":"Payment", "confidentiality":"Confidentiality", "intellectual_property":"Intellectual Property", "non_compete":"Non-compete / Non-solicitation", "non_solicitation":"Non-compete / Non-solicitation", "liability":"Liability", "dispute_resolution":"Dispute Resolution", "governing_law":"Governing Law", "renewal":"Renewal", "unknown":"Unknown"}
    ar = {"termination":"الإنهاء", "payment":"الدفع", "confidentiality":"السرية", "intellectual_property":"الملكية الفكرية", "non_compete":"القيود التنافسية وعدم الاستقطاب", "non_solicitation":"القيود التنافسية وعدم الاستقطاب", "liability":"المسؤولية", "dispute_resolution":"حل النزاعات", "governing_law":"القانون الحاكم", "renewal":"التجديد", "unknown":"غير محدد"}
    return (ar if lang == "ar" else en).get(key, safe_text(value, "غير محدد" if lang == "ar" else "Not specified"))


def format_risk_level(value: Any, lang: str | None = None) -> str:
    lang = lang or current_lang()
    key = safe_text(value, "").lower()
    en = {"high":"High", "medium":"Medium", "low":"Low", "critical":"Critical", "found":"Found", "missing":"Missing", "partial":"Partial", "moderate alignment":"Moderate alignment", "strong alignment":"Strong alignment", "needs strengthening":"Needs strengthening"}
    ar = {"high":"مرتفع", "medium":"متوسط", "low":"منخفض", "critical":"حرج", "found":"موجود", "missing":"مفقود", "partial":"جزئي", "moderate alignment":"توافق متوسط", "strong alignment":"توافق قوي", "needs strengthening":"يحتاج إلى تقوية", "مرتفع":"مرتفع", "متوسط":"متوسط", "منخفض":"منخفض"}
    return (ar if lang == "ar" else en).get(key, safe_text(value, "غير محدد" if lang == "ar" else "Not specified"))


def format_priority(value: Any, lang: str | None = None) -> str:
    return format_risk_level(value, lang)


def format_decision(value: Any, lang: str | None = None) -> str:
    lang = lang or current_lang()
    key = safe_text(value, "").lower()
    en = {"ready for business review":"Ready for business review", "needs revision":"Needs revision", "needs legal review":"Needs legal review", "high risk - do not sign yet":"High risk - do not sign yet", "acceptable":"Acceptable", "needs strengthening":"Needs strengthening", "needs clarification":"Needs clarification", "missing":"Missing", "high risk":"High risk", "needs review":"Needs review"}
    ar = {"ready for business review":"جاهز للمراجعة التجارية", "needs revision":"يحتاج إلى تعديل", "needs legal review":"يحتاج إلى مراجعة قانونية", "high risk - do not sign yet":"خطر مرتفع - لا توقّع الآن", "acceptable":"مقبول", "needs strengthening":"يحتاج إلى تقوية", "needs clarification":"يحتاج إلى توضيح", "missing":"مفقود", "high risk":"خطر مرتفع", "needs review":"يحتاج إلى مراجعة", "مقبول للمراجعة التجارية":"مقبول للمراجعة التجارية", "يحتاج إلى تقوية":"يحتاج إلى تقوية", "يحتاج إلى توضيح":"يحتاج إلى توضيح", "مفقود":"مفقود", "يحتاج إلى مراجعة قانونية":"يحتاج إلى مراجعة قانونية"}
    return (ar if lang == "ar" else en).get(key, safe_text(value, "يحتاج إلى مراجعة" if lang == "ar" else "Needs review"))


def format_source(value: Any, lang: str | None = None) -> str:
    lang = lang or current_lang()
    key = safe_text(value, "").lower()
    ar = {"extracted_text":"نص العقد المستخرج", "extracted_contract_text":"نص العقد المستخرج", "rule_based":"مطابقة قائمة على القواعد", "hybrid":"ذكاء اصطناعي + قواعد", "degraded":"وضع احتياطي", "illustrative benchmark comparison":"مقارنة مرجعية توضيحية", "template alignment and contract completeness comparison":"مقارنة اكتمال ومواءمة مع قالب داخلي", "contract_specific":"إجابة مرتبطة بالعقد", "general_contract_concept":"شرح عام لمفهوم تعاقدي", "small_talk":"محادثة عامة", "app_help":"مساعدة في التطبيق", "unrelated_general":"إجابة عامة"}
    en = {"extracted_text":"Extracted contract text", "extracted_contract_text":"Extracted contract text", "rule_based":"Rule-based match", "hybrid":"Hybrid AI + rule-based", "degraded":"Rule-based fallback", "illustrative benchmark comparison":"Illustrative benchmark comparison", "template alignment and contract completeness comparison":"Template alignment and contract completeness comparison", "contract_specific":"Contract-specific answer", "general_contract_concept":"General contract concept", "small_talk":"Small talk", "app_help":"App help", "unrelated_general":"General answer"}
    return (ar if lang == "ar" else en).get(key, safe_text(value, "غير محدد" if lang == "ar" else "Not specified"))


def localized_review_item(text: Any) -> str:
    value = safe_text(text, "")
    if current_lang() != "ar":
        return value
    replacements = {
        "Review Termination": "مراجعة بند الإنهاء",
        "Review Payment": "مراجعة بند الدفع",
        "Review Liability": "مراجعة بند المسؤولية",
        "Review Intellectual Property": "مراجعة بند الملكية الفكرية",
        "Review Confidentiality": "مراجعة بند السرية",
        "Review Dispute Resolution": "مراجعة بند حل النزاعات",
        "Review Governing Law": "مراجعة بند القانون الحاكم",
        "Fix or add Termination before signing.": "أصلح أو أضف بند الإنهاء قبل التوقيع.",
        "Fix or add Payment before signing.": "أصلح أو أضف بند الدفع قبل التوقيع.",
        "Fix or add Liability before signing.": "أصلح أو أضف بند المسؤولية قبل التوقيع.",
        "appears acceptable for business review based on current evidence.": "يبدو مقبولًا للمراجعة التجارية بناءً على الأدلة الحالية.",
    }
    for en, ar in replacements.items():
        value = value.replace(en, ar)
    return value


def render_global_css() -> None:
    direction = "rtl" if is_rtl() else "ltr"
    st.markdown(build_app_css(st.session_state.get("theme", "light"), direction), unsafe_allow_html=True)


def render_page_header(page: str, quick_label: str | None = None) -> None:
    title = t(f"page.{page}.title", page)
    subtitle = t(f"page.{page}.subtitle", "")
    quick = f'<span class="cip-pill">{safe_html(quick_label)}</span>' if quick_label else ""
    st.markdown(f'<div class="cip-shell-topbar"><div class="cip-page-title"><h1>{safe_html(title)}</h1><p>{safe_html(subtitle)}</p></div><div>{quick}</div></div>', unsafe_allow_html=True)


def render_empty_state(title: str, body: str) -> None:
    st.markdown(f'<div class="cip-empty-state"><strong>{safe_html(title)}</strong><br>{safe_html(body)}</div>', unsafe_allow_html=True)


def init_state():
    defaults = {"token": None, "user": None, "page": "Home", "theme": "light", "language": "en", "auth_mode": "login", "selected_contract_id": None, "last_analysis": None, "last_analysis_contract_id": None, "last_analysis_at": None, "analysis_result": None, "analysis_contract_label": None, "analysis_contract_id": None, "analysis_endpoint": None, "last_api_debug": None, "chat_history": [], "chat_contract_id": None, "chat_contract_label": None, "last_chat_debug": None, "benchmark_result": None, "benchmark_contract_id": None, "ai_explanation_language": "match", "report_language": "match", "analysis_report_pdf": None, "analysis_report_filename": None}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def apply_user_preferences(user: dict[str, Any] | None) -> None:
    prefs = (user or {}).get("preferences") or {}
    for key in ["theme", "language", "ai_explanation_language", "report_language"]:
        if prefs.get(key):
            st.session_state[key] = prefs[key]


def save_user_preferences() -> None:
    if not st.session_state.get("token"):
        return
    api_request("PUT", "/auth/preferences", json={
        "theme": st.session_state.theme,
        "language": st.session_state.language,
        "ai_explanation_language": st.session_state.ai_explanation_language,
        "report_language": st.session_state.report_language,
    })


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
            if isinstance(detail, dict):
                message = detail.get("detail") or detail.get("message") or "Backend returned an internal error."
                return False, {"message": safe_text(message), "error_code": detail.get("error_code"), "explanation_language": detail.get("explanation_language"), "ui_language": detail.get("ui_language"), **debug}
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


def api_download(path: str, timeout: int = 90) -> tuple[bool, Any, str | None]:
    headers = {}
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    url = f"{API_BASE_URL}{path}"
    debug = {"method": "GET", "base_url": API_BASE_URL, "path": path, "url": url, "status_code": None, "response_body": None, "error": None}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        debug["status_code"] = response.status_code
        st.session_state.last_api_debug = debug
        if response.ok:
            disposition = response.headers.get("content-disposition", "")
            filename = None
            if "filename=" in disposition:
                filename = disposition.split("filename=", 1)[1].strip('"')
            return True, response.content, filename
        body = parse_response_body(response)
        debug["response_body"] = body
        message = body.get("detail") if isinstance(body, dict) else body
        return False, {"message": safe_text(message, "Report generation failed."), **debug}, None
    except requests.RequestException as exc:
        debug["error"] = str(exc)
        st.session_state.last_api_debug = debug
        return False, {"message": "Report download request failed.", **debug}, None


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
    why_label = localized_label("Why this matters", "لماذا هذا مهم")
    clause_label = localized_label("Related clause", "البند المرتبط")
    source_label = localized_label("Source", "المصدر")
    priority = format_priority(action.get("priority"))
    related = format_clause_type(action.get("related_clause")) if current_lang() == "ar" else safe_text(action.get("related_clause"), "Not specified")
    st.markdown(f'<div class="cip-action-card"><div class="cip-card-header"><h4>{safe_html(localized_review_item(action["action"]))}</h4><span class="{badge_class(action["priority"])}">{safe_html(priority)}</span></div><p><strong>{safe_html(why_label)}:</strong> {safe_html(localized_review_item(action["rationale"]))}</p><p><strong>{safe_html(clause_label)}:</strong> {safe_html(related)}</p><p><strong>{safe_html(source_label)}:</strong> {safe_html(format_source(action["source"]))}</p></div>', unsafe_allow_html=True)


def render_overall_visual(analysis: dict[str, Any]) -> None:
    score = analysis.get("health_score")
    score_number = int(score) if isinstance(score, (int, float)) else 0
    risk = analysis.get("risk_level", "Not specified")
    summary = plain_value(analysis.get("ai_overall_assessment"), "The analysis provides decision support based on extracted evidence and missing details.")
    decision = analysis.get("review_decision", {})
    decision_label = format_decision(decision.get("review_decision")) if isinstance(decision, dict) else format_decision("Needs review")
    width = max(0, min(100, score_number))
    explanation = "This contract appears generally strong, but review the decision drivers before signing." if score_number >= 80 else "This contract needs revision or focused review before signing."
    health_label = localized_label("Contract Health", "صحة العقد")
    decision_text = localized_label("AI decision", "قرار الذكاء الاصطناعي")
    risk_text = localized_label("Risk", "المخاطر")
    st.markdown(f'<div class="cip-score-meter"><div class="cip-card-header"><div><div class="cip-eyebrow">{safe_html(health_label)}</div><div class="cip-score-value technical-value">{score_number}/100</div></div><span class="{badge_class(risk)}">{safe_html(format_risk_level(risk))} {safe_html(risk_text)}</span></div><div class="cip-score-track"><span class="cip-score-fill" style="width:{width}%"></span></div><p>{safe_html(explanation)}</p><p><strong>{safe_html(decision_text)}:</strong> {safe_html(decision_label)}</p><p class="cip-muted">{safe_html(summary)}</p></div>', unsafe_allow_html=True)

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
        return f"Fallback review point: add a clear {label} clause tailored to this deal before signature."
    recommendations = {
        "termination": "Fallback review point: confirm notice period, cure period, termination for cause, and survival language are complete.",
        "payment": "Fallback review point: confirm amounts, due dates, late fees, taxes, invoice process, and disputed-payment rights.",
        "confidentiality": "Fallback review point: confirm exclusions, permitted disclosures, duration, and return/destruction obligations.",
        "liability": "Fallback review point: confirm liability caps, excluded damages, indemnities, and exceptions are commercially acceptable.",
        "intellectual_property": "Fallback review point: confirm ownership, licenses, deliverables, and pre-existing IP rights are explicit.",
        "governing_law": "Fallback review point: confirm governing law and venue are acceptable to the business.",
        "dispute_resolution": "Fallback review point: confirm escalation, forum, timing, and interim relief rights are workable.",
        "renewal": "Fallback review point: confirm renewal term, notice window, price changes, and opt-out rights are clear.",
    }
    return recommendations.get(clause_type, f"Fallback review point: review the {label} clause for completeness and negotiation risk.")


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
        "why_it_matters": plain_value(clause.get("why_it_matters") or clause.get("ai_insight"), clause_summary(clause_type, status)),
        "risk_in_plain_english": plain_value(clause.get("risk_in_plain_english") or clause.get("ai_risk_assessment"), "Review whether the clause is complete, balanced, and clear enough for the business use case."),
        "what_to_check_next": plain_value(clause.get("what_to_check_next"), generic_recommendation(clause_type, status)),
        "completeness": safe_text(clause.get("completeness"), "Partial" if status != "missing" else "Missing"),
        "extracted_details": clause.get("extracted_details") or {},
        "risk": safe_text(clause.get("risk") or clause.get("risk_level"), "Not specified"),
        "recommendation": safe_text(clause.get("ai_recommendation") or clause.get("recommendation") or clause.get("suggested_improvement"), generic_recommendation(clause_type, status)),
        "ai_insight": safe_text(clause.get("ai_insight"), clause_summary(clause_type, status)),
        "ai_risk_assessment": safe_text(clause.get("ai_risk_assessment"), "Review whether the clause is complete, balanced, and clear enough for the business use case."),
        "ai_recommendation": safe_text(clause.get("ai_recommendation"), generic_recommendation(clause_type, status)),
        "negotiation_note": safe_text(clause.get("negotiation_note"), "Discuss clearer limits, responsibilities, exceptions, and approval steps if this clause affects the business deal."),
        "clause_decision": safe_text(clause.get("clause_decision"), "Needs review"),
        "business_impact": safe_text(clause.get("business_impact"), "This clause may affect business responsibilities, timing, money, restrictions, or legal exposure."),
        "decision_risk_level": safe_text(clause.get("risk_level"), "Medium"),
        "why_this_decision": safe_text(clause.get("why_this_decision"), clause.get("ai_risk_assessment") or "Decision is based on extracted evidence and missing details."),
        "recommended_fix": safe_text(clause.get("recommended_fix"), clause.get("ai_recommendation") or generic_recommendation(clause_type, status)),
        "questions_to_ask": clause.get("questions_to_ask") or [],
        "review_priority": safe_text(clause.get("priority") or clause.get("review_priority"), "Medium"),
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


def normalize_key_term(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {"term": f"Key term {index + 1}", "extracted_value": item}
    evidence = normalize_evidence(item.get("evidence") or item.get("sources"))
    return {
        "term": safe_text(item.get("term") or item.get("name"), f"Key term {index + 1}"),
        "extracted_value": plain_value(item.get("extracted_value") or item.get("value"), "Not found in extracted text"),
        "evidence": evidence,
        "evidence_source": safe_text(item.get("evidence_source") or (evidence[0].get("source") if evidence else None), "Extracted contract text"),
        "simple_explanation": plain_value(item.get("simple_explanation"), "This is an important business term extracted from the contract evidence."),
        "risk_or_verify": plain_value(item.get("risk_or_verify") or item.get("what_to_verify"), "Confirm this value against the original contract and responsible business owner."),
        "confidence": safe_text(item.get("confidence"), "Medium — evidence was found, but the value should be confirmed."),
    }


def normalize_analysis_response(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    clauses = [normalize_clause(clause, idx) for idx, clause in enumerate(data.get("clauses") or [])]
    key_terms = [normalize_key_term(item, idx) for idx, item in enumerate(data.get("key_terms") or [])]
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
        "active_model": safe_text(data.get("model_used") or data.get("active_model") or data.get("model"), "Not specified"),
        "confidence": safe_text(data.get("confidence"), "Low" if data.get("degraded_mode") else "Medium"),
        "executive_summary": safe_text(data.get("executive_summary") or data.get("summary"), "No executive summary returned."),
        "ai_overall_assessment": plain_value(data.get("ai_overall_assessment"), "Decision support is based on extracted evidence, missing details, and clause-level risk signals."),
        "key_terms": key_terms,
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
        "review_decision": data.get("review_decision") or {},
        "priority_action_plan": data.get("priority_action_plan") or {},
        "follow_up_questions": data.get("follow_up_questions") or [],
        "contract_type_label": safe_text(data.get("contract_type_label") or data.get("contract_type"), "Not detected"),
        "contract_type_confidence": data.get("contract_type_confidence"),
        "score_dimensions": data.get("score_dimensions") or {},
        "extraction_metadata": data.get("extraction_metadata") or {},
        "embedding_status": data.get("embedding_status") or {},
        "retrieval_status": data.get("retrieval_status") or {},
        "reviewer_used": bool(data.get("reviewer_used", False)),
        "reviewer_status": safe_text(data.get("reviewer_status"), "Not used"),
        "explanation_language": safe_text(data.get("explanation_language"), effective_explanation_language()),
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
    if analysis.get("contract_type_label") != "Not detected":
        confidence = analysis.get("contract_type_confidence")
        st.caption(f"Contract type: {analysis['contract_type_label']} · Confidence: {confidence if confidence is not None else 'Not scored'}")
    retrieval = analysis.get("retrieval_status") or {}
    embedding = analysis.get("embedding_status") or {}
    st.caption(" • ".join([
        f"Reviewer used: {format_bool(analysis.get('reviewer_used'))}",
        f"Retrieval: {retrieval.get('mode', 'hybrid')}",
        f"Embeddings: {format_bool(embedding.get('embedding_used') or retrieval.get('embedding_used'))}",
    ]))
    if analysis.get("score_dimensions"):
        st.caption("Score dimensions: " + plain_value(analysis["score_dimensions"]))


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
        evidence_label = localized_label("Evidence", "الدليل")
        source_label = localized_label("Source", "المصدر")
        location_label = localized_label("Location", "الموقع")
        keyword_label = localized_label("Keyword", "الكلمة المفتاحية")
        confidence_label = localized_label("Confidence", "الثقة")
        st.markdown(f'<div class="cip-evidence"><div class="cip-evidence-meta">{safe_html(evidence_label)} {idx} · {safe_html(source_label)}: {safe_html(format_source(source))} · {safe_html(location_label)}: <span class="technical-value">{safe_html(location)}</span> · {safe_html(keyword_label)}: <span class="technical-value">{safe_html(keyword)}</span> · {safe_html(confidence_label)}: {safe_html(confidence)}</div><blockquote>{safe_html(item.get("text"), "No direct evidence captured for this clause.")}</blockquote></div>', unsafe_allow_html=True)


def render_chat_evidence(evidence: list[dict[str, Any]], lang: str | None = None) -> None:
    lang = lang or effective_explanation_language()
    if not evidence:
        st.caption(localized_label_for(lang, "No contract evidence was used for this answer.", "لم يتم استخدام دليل من العقد لهذه الإجابة."))
        return
    for idx, item in enumerate(evidence, start=1):
        clause = item.get("clause") or "Relevant contract text"
        source = item.get("source") or "extracted_contract_text"
        location = item.get("location") or "Extracted contract text"
        text = item.get("text") or "No direct evidence captured."
        card_label = localized_label_for(lang, "Card", "بطاقة")
        clause_label = localized_label_for(lang, "Clause", "البند")
        source_label = localized_label_for(lang, "Source", "المصدر")
        location_label = localized_label_for(lang, "Location", "الموقع")
        why_text = localized_label_for(lang, "Why it matters: this is the contract text used to support the answer.", "سبب الأهمية: هذا هو نص العقد المستخدم لدعم الإجابة.")
        st.markdown(f'<div class="cip-evidence"><div class="cip-evidence-meta">{safe_html(card_label)} {idx} · {safe_html(clause_label)}: {safe_html(format_clause_type(clause, lang))} · {safe_html(source_label)}: {safe_html(format_source(source, lang))} · {safe_html(location_label)}: <span class="technical-value">{safe_html(location)}</span></div><blockquote>{safe_html(text)}</blockquote><div class="cip-muted">{safe_html(why_text)}</div></div>', unsafe_allow_html=True)


def confidence_human(confidence: Any, label: str | None = None, lang: str | None = None) -> str:
    lang = lang or effective_explanation_language()
    if label:
        return label
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return "الثقة: متوسطة — يجب تأكيد الإجابة بالرجوع إلى العقد." if lang == "ar" else "Medium — this answer should be confirmed against the contract."
    if lang == "ar":
        if value >= 0.8:
            return "الثقة: عالية — العقد يذكر هذه النقطة بوضوح."
        if value >= 0.5:
            return "الثقة: متوسطة — العقد يجيب جزئيًا، لكن بعض التفاصيل تحتاج إلى تأكيد."
        return "الثقة: منخفضة — العقد لا يجيب عن هذه النقطة بوضوح."
    if value >= 0.8:
        return "High — the contract clearly mentions this."
    if value >= 0.5:
        return "Medium — the contract partly answers this, but some details should be confirmed."
    return "Low — the contract does not clearly answer this."


def render_assistant_message(message: dict[str, Any]) -> None:
    lang = message.get("response_language") or message.get("explanation_language") or effective_explanation_language()
    assistant_label = localized_label_for(lang, "Contract Assistant", "مساعد العقود")
    summary_label = localized_label_for(lang, "Simple summary", "ملخص مبسط")
    note_label = localized_label_for(lang, "Practical note", "ملاحظة عملية")
    used_contract_label = localized_label_for(lang, "Used contract", "تم استخدام العقد")
    llm_label = localized_label_for(lang, "LLM used", "تم استخدام الذكاء الاصطناعي")
    st.markdown(f'<div class="cip-assistant-bubble"><div class="cip-eyebrow">{safe_html(assistant_label)} · {safe_html(format_source(message.get("answer_type"), lang))}</div><p>{safe_html(message.get("content"), "")}</p><p><strong>{safe_html(summary_label)}:</strong> {safe_html(message.get("plain_english_summary"), "")}</p><p><strong>{safe_html(note_label)}:</strong> {safe_html(message.get("practical_note"), "")}</p><div class="cip-card-meta"><span>{safe_html(confidence_human(message.get("confidence"), message.get("confidence_label"), lang))}</span><span>{safe_html(used_contract_label)}: {safe_html(format_bool(message.get("used_contract"), lang))}</span><span>{safe_html(llm_label)}: {safe_html(format_bool(message.get("llm_used"), lang))}</span><span>{safe_html(localized_label_for(lang, "Model", "النموذج"))}: {safe_html(message.get("model_used") or "fallback")}</span></div></div>', unsafe_allow_html=True)
    with st.expander(localized_label_for(lang, "Evidence used", "الأدلة المستخدمة"), expanded=False):
        render_chat_evidence(message.get("evidence") or [], lang)
    suggestions = message.get("follow_up_suggestions") or []
    if suggestions:
        st.markdown(f"**{localized_label_for(lang, 'Suggested follow-ups', 'أسئلة متابعة مقترحة')}**")
        st.markdown(" ".join(f'<span class="cip-suggestion-chip">{safe_html(item)}</span>' for item in suggestions[:4]), unsafe_allow_html=True)


def append_chat_message(role: str, content: str, **metadata: Any) -> None:
    item = {"role": role, "content": content, "timestamp": datetime.now().strftime("%H:%M:%S")}
    item.update(metadata)
    st.session_state.chat_history.append(item)


def render_clause_card(clause: dict[str, Any]) -> None:
    status_class = badge_class(clause["status"])
    priority_class = badge_class(clause["review_priority"])
    review_label = localized_label("AI Review by Clause", "مراجعة الذكاء الاصطناعي للبند")
    decision_label = localized_label("AI decision", "قرار الذكاء الاصطناعي")
    risk_label = localized_label("Risk", "المخاطر")
    priority_label = localized_label("Priority", "الأولوية")
    source_label = localized_label("Source", "المصدر")
    st.markdown(f'<div class="cip-review-card"><div class="cip-card-header"><div><div class="cip-eyebrow">{safe_html(review_label)}</div><h3>{safe_html(clause["title"])}</h3></div><span class="{status_class}">{safe_html(format_risk_level(clause["status"]))}</span></div><div class="cip-card-meta"><span class="{badge_class(clause["clause_decision"])}">{safe_html(decision_label)}: {safe_html(format_decision(clause["clause_decision"]))}</span><span class="{badge_class(clause["decision_risk_level"])}">{safe_html(risk_label)}: {safe_html(format_risk_level(clause["decision_risk_level"]))}</span><span class="{priority_class}">{safe_html(priority_label)}: {safe_html(format_priority(clause["review_priority"]))}</span><span>{safe_html(source_label)}: <span class="technical-value">{safe_html(clause["location"])}</span></span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-layman-box"><strong>{safe_html(localized_label("Simple explanation", "شرح مبسط"))}</strong><br>{safe_html(clause["simple_explanation"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-ai-box"><strong>{safe_html(localized_label("Why it matters", "لماذا هذا مهم"))}:</strong><br>{safe_html(clause["why_it_matters"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-ai-box"><strong>{safe_html(localized_label("Risk in plain language", "الخطر ببساطة"))}:</strong><br>{safe_html(clause["risk_in_plain_english"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-recommendation"><strong>{safe_html(localized_label("What to check next", "ما الذي يجب التأكد منه"))}:</strong> {safe_html(clause["what_to_check_next"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-negotiation"><strong>{safe_html(localized_label("Why this decision", "سبب القرار"))}:</strong> {safe_html(clause["why_this_decision"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-recommendation"><strong>{safe_html(localized_label("Recommended fix", "الإصلاح المقترح"))}:</strong> {safe_html(clause["recommended_fix"])}</div>', unsafe_allow_html=True)
    if clause.get("questions_to_ask"):
        st.markdown(" ".join(f'<span class="cip-suggestion-chip">{safe_html(q)}</span>' for q in clause["questions_to_ask"]), unsafe_allow_html=True)
    st.markdown(f"**{localized_label('Evidence from contract', 'الدليل من العقد')}**")
    render_evidence(clause["evidence"])
    st.markdown(f"**{localized_label('Key details extracted', 'التفاصيل الرئيسية المستخرجة')}**")
    render_clause_details(clause)
    st.markdown(f'<div class="cip-card-meta"><span>{safe_html(localized_label("Completeness", "الاكتمال"))}: {safe_html(format_risk_level(clause["completeness"]))}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-recommendation"><strong>{safe_html(localized_label("AI recommendation", "توصية الذكاء الاصطناعي"))}:</strong> {safe_html(clause["ai_recommendation"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cip-negotiation"><strong>{safe_html(localized_label("Negotiation note", "ملاحظة تفاوضية"))}:</strong> {safe_html(clause["negotiation_note"])}</div>', unsafe_allow_html=True)


def render_risk_card(risk: dict[str, str]) -> None:
    affected_label = localized_label("Affected clause", "البند المتأثر")
    rec_label = localized_label("Recommendation", "التوصية")
    st.markdown(f'<div class="cip-risk-card"><div class="cip-card-header"><h4>{safe_html(risk["title"])}</h4><span class="{badge_class(risk["severity"])}">{safe_html(format_risk_level(risk["severity"]))}</span></div><p>{safe_html(risk["explanation"])}</p><p><strong>{safe_html(affected_label)}:</strong> {safe_html(format_clause_type(risk["affected_clause"]))}</p><p><strong>{safe_html(rec_label)}:</strong> {safe_html(risk["recommendation"])}</p></div>', unsafe_allow_html=True)


def render_missing_clause_card(name: str) -> None:
    label = format_clause_type(name)
    priority_label = localized_label("High Priority", "أولوية مرتفعة")
    why_label = localized_label("Why it matters", "لماذا هذا مهم")
    wording_label = localized_label("Suggested wording direction", "اتجاه الصياغة المقترح")
    st.markdown(f'<div class="cip-missing-card"><div class="cip-card-header"><h4>{safe_html(label)}</h4><span class="cip-badge cip-badge-red">{safe_html(priority_label)}</span></div><p><strong>{safe_html(why_label)}:</strong> {safe_html(clause_summary(safe_text(name).lower(), "missing"))}</p><p><strong>{safe_html(wording_label)}:</strong> {safe_html(generic_recommendation(safe_text(name).lower(), "missing"))}</p></div>', unsafe_allow_html=True)


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
        "benchmark_mode": safe_text(data.get("benchmark_mode"), "Template alignment and contract completeness comparison"),
        "benchmark_limitation": safe_text(data.get("benchmark_limitation"), "Internal checklist comparison, not market/legal market data."),
        "profile_used": safe_text(data.get("profile_used"), "Generic commercial contract"),
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


def service_status_label(ok: bool, degraded: bool = False) -> str:
    if ok and not degraded:
        return "Healthy"
    if ok and degraded:
        return "Degraded"
    return "Offline"


def render_status_card(title: str, status: str, key_value: Any, explanation: str, checked_at: str = "Now") -> None:
    checked_label = localized_label("Last checked", "آخر فحص")
    display_value = format_bool(key_value) if isinstance(key_value, bool) else key_value
    st.markdown(f'<div class="cip-status-card"><div class="cip-card-header"><h4>{safe_html(title)}</h4><span class="{badge_class(status)}">{safe_html(localized_status(status))}</span></div><p><strong>{safe_html(display_value)}</strong></p><p>{safe_html(explanation)}</p><div class="cip-muted">{safe_html(checked_label)}: {safe_html(checked_at)}</div></div>', unsafe_allow_html=True)


def endpoint_status_row(name: str, status: str, status_code: Any, explanation: str) -> None:
    status_label = localized_label("Status", "الحالة")
    st.markdown(f'<div class="cip-endpoint-row"><strong class="technical-value">{safe_html(name)}</strong><span class="{badge_class(status)}">{safe_html(localized_status(status))}</span><span>{safe_html(status_label)}: <span class="technical-value">{safe_html(status_code)}</span></span><span>{safe_html(explanation)}</span></div>', unsafe_allow_html=True)


def run_endpoint_checks() -> list[dict[str, Any]]:
    checks = []
    for method, path, label in [("GET", "/healthz", "/healthz"), ("GET", "/auth/me", "/auth/me"), ("GET", "/clients", "/clients"), ("GET", "/contracts", "/contracts"), ("GET", "/llm/health", "/llm/health")]:
        ok, data = api_request(method, path, timeout=10)
        debug = st.session_state.last_api_debug or {}
        checks.append({"name": label, "status": "Healthy" if ok else "Failed", "status_code": debug.get("status_code"), "explanation": "Endpoint responded successfully." if ok else user_message(data)})
    ok, contracts = api_request("GET", "/contracts", timeout=10)
    contract_id = None
    if ok and contracts:
        contract_id = (contracts[0].get("id") or contracts[0].get("_id"))
    for suffix in ["analyze", "chat", "benchmark"]:
        path = f"/contracts/{{id}}/{suffix}"
        if contract_id:
            checks.append({"name": path, "status": "Skipped", "status_code": "not run", "explanation": "Skipped to avoid side effects; available for the selected contract workflow."})
        else:
            checks.append({"name": path, "status": "Skipped", "status_code": "no contract", "explanation": "Skipped — no contract available for this user."})
    return checks


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
    st.info(result.get("benchmark_limitation") or "Internal checklist comparison, not market/legal market data.")
    st.caption(f"Profile used: {result.get('profile_used', 'Generic commercial contract')}")
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


def render_key_terms(terms: list[dict[str, Any]]) -> None:
    st.markdown("### Key Terms Extracted")
    if not terms:
        render_empty_state("Key Terms Extracted", "No precise key terms were extracted yet. Run analysis again with a clearer contract scan if this seems wrong.")
        return
    for term in terms:
        st.markdown(f'<div class="cip-review-card"><div class="cip-card-header"><h4>{safe_html(term["term"])}</h4><span class="{badge_class(term["confidence"])}">{safe_html(term["confidence"])}</span></div><p><strong>Extracted value:</strong> {safe_html(term["extracted_value"])}</p><p><strong>Simple explanation:</strong> {safe_html(term["simple_explanation"])}</p><p><strong>Risk / what to verify:</strong> {safe_html(term["risk_or_verify"])}</p><p><strong>Evidence source:</strong> {safe_html(term["evidence_source"])}</p></div>', unsafe_allow_html=True)
        render_evidence(term.get("evidence") or [])


def render_clause_details(clause: dict[str, Any]) -> None:
    details = clause.get("extracted_details") or {}
    if not details:
        st.caption("No additional structured details were extracted for this clause.")
        return
    chips = []
    for key, value in details.items():
        chips.append(f'<span>{safe_html(titleize(key))}: {safe_html(plain_value(value))}</span>')
    st.markdown(f'<div class="cip-card-meta">{"".join(chips[:10])}</div>', unsafe_allow_html=True)


def render_ai_decision(analysis: dict[str, Any]) -> None:
    decision = analysis.get("review_decision") or {}
    if not isinstance(decision, dict):
        decision = {}
    st.markdown("### Overall AI Decision")
    why_label = localized_label("Why", "سبب القرار")
    human_label = localized_label("Human review required", "تتطلب مراجعة بشرية")
    confidence = format_risk_level(decision.get("decision_confidence", "Medium"))
    st.markdown(f'<div class="cip-summary-card"><div class="cip-card-header"><h3>{safe_html(format_decision(decision.get("review_decision", "Needs review")))}</h3><span class="{badge_class(decision.get("decision_confidence", "Medium"))}">{safe_html(confidence)}</span></div><p><strong>{safe_html(why_label)}:</strong> {safe_html(decision.get("decision_reasoning", "Decision support is based on extracted evidence, missing details, and clause-level risks."))}</p><p><strong>{safe_html(human_label)}:</strong> {safe_html(format_bool(decision.get("human_review_required", True)))}</p></div>', unsafe_allow_html=True)
    for label, key in [(localized_label("Must fix before signing", "يجب إصلاحه قبل التوقيع"), "must_fix_before_signing"), (localized_label("Should review", "ينبغي مراجعته"), "should_review"), (localized_label("Acceptable points", "نقاط مقبولة"), "acceptable_points")]:
        items = decision.get(key) or []
        if items:
            st.markdown(f"**{label}**")
            for item in items[:5]:
                st.markdown(f'<div class="cip-check-item">• {safe_html(localized_review_item(item))}</div>', unsafe_allow_html=True)


def render_priority_action_plan(analysis: dict[str, Any]) -> None:
    plan = analysis.get("priority_action_plan") or {}
    st.markdown("### Priority Action Plan")
    for label, key in [(localized_label("Must fix before signing", "يجب إصلاحه قبل التوقيع"), "must_fix_before_signing"), (localized_label("Should clarify", "ينبغي توضيحه"), "should_clarify"), (localized_label("Good to confirm", "من الجيد تأكيده"), "good_to_confirm"), (localized_label("Optional improvements", "تحسينات اختيارية"), "optional_improvements")]:
        items = plan.get(key) or []
        if items:
            st.markdown(f"**{label}**")
            for item in items:
                owner_label = localized_label("Owner", "المالك")
                owner_value = item.get('owner_suggestion', 'Business Owner')
                if current_lang() == "ar":
                    owner_value = {"Legal": "القانوني", "Business Owner": "مسؤول الأعمال", "HR": "الموارد البشرية", "Finance": "المالية"}.get(owner_value, owner_value)
                source_text = f"{owner_label}: {owner_value} · {item.get('evidence_basis', localized_label('Evidence-based decision support', 'دعم قرار مبني على الأدلة'))}"
                render_action_card({"action": item.get("action"), "rationale": item.get("reason"), "related_clause": item.get("related_clause"), "priority": item.get("priority"), "source": source_text})


def render_analysis_results(analysis: dict[str, Any]) -> None:
    render_score_cards(analysis)
    render_ai_decision(analysis)
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
        for item in analysis["recommended_improvements"] or [normalize_action("Review extracted terms and confirm business/legal assumptions before signature.")]:
            action = normalize_action(item)
            st.markdown(f'<div class="cip-check-item">→ {safe_html(action["action"])}</div>', unsafe_allow_html=True)

    render_key_terms(analysis.get("key_terms") or [])

    st.markdown("### Contract Health / Risk Overview")
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

    render_priority_action_plan(analysis)

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
    st.sidebar.markdown(f'<div class="cip-brand-card"><div class="cip-brand-title">⚖️ {safe_html(t("app.name"))}</div><div class="cip-brand-subtitle">{safe_html(t("app.subtitle"))}</div><div class="cip-card-meta"><span>{safe_html(t("label.frontend_build"))}: {FRONTEND_BUILD}</span></div></div>', unsafe_allow_html=True)
    theme_label_to_value = {t("theme.light"): "light", t("theme.dark"): "dark"}
    current_theme_label = t("theme.dark") if st.session_state.theme == "dark" else t("theme.light")
    selected_theme = st.sidebar.selectbox(t("label.theme"), list(theme_label_to_value.keys()), index=list(theme_label_to_value.keys()).index(current_theme_label))
    selected_theme_value = theme_label_to_value[selected_theme]
    if selected_theme_value != st.session_state.theme:
        st.session_state.theme = selected_theme_value
        save_user_preferences()
        st.rerun()
    lang_label_to_value = {t("language.english"): "en", t("language.arabic"): "ar"}
    current_lang_label = t("language.arabic") if st.session_state.language == "ar" else t("language.english")
    selected_lang = st.sidebar.selectbox(t("label.language"), list(lang_label_to_value.keys()), index=list(lang_label_to_value.keys()).index(current_lang_label))
    selected_lang_value = lang_label_to_value[selected_lang]
    if selected_lang_value != st.session_state.language:
        st.session_state.language = selected_lang_value
        save_user_preferences()
        st.rerun()
    expl_options = {"Match interface language": "match", "English": "en", "العربية": "ar"}
    current_expl = next(label for label, value in expl_options.items() if value == st.session_state.ai_explanation_language)
    selected_expl = st.sidebar.selectbox(t("label.ai_explanation_language"), list(expl_options.keys()), index=list(expl_options.keys()).index(current_expl))
    selected_expl_value = expl_options[selected_expl]
    if selected_expl_value != st.session_state.ai_explanation_language:
        st.session_state.ai_explanation_language = selected_expl_value
        save_user_preferences()
    report_options = {"Match interface language": "match", "English": "en", "العربية": "ar"}
    current_report = next(label for label, value in report_options.items() if value == st.session_state.report_language)
    selected_report = st.sidebar.selectbox(t("label.report_language"), list(report_options.keys()), index=list(report_options.keys()).index(current_report))
    selected_report_value = report_options[selected_report]
    if selected_report_value != st.session_state.report_language:
        st.session_state.report_language = selected_report_value
        save_user_preferences()
    st.sidebar.caption(t("label.active_frontend"))
    st.sidebar.caption(t("label.active_file"))
    st.sidebar.caption(f"{t('label.backend_build')}: {health.get('Backend Build', 'unknown')}")
    if st.session_state.user:
        st.sidebar.divider()
        st.sidebar.caption(t("label.signed_in_as"))
        st.sidebar.write(st.session_state.user.get("email"))
        if st.sidebar.button(t("action.logout"), use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()
        st.sidebar.divider()
        for group_key, items in NAV_GROUPS:
            st.sidebar.markdown(f'<div class="cip-nav-group">{safe_html(t(group_key))}</div>', unsafe_allow_html=True)
            for page, icon in items:
                label = f"{icon} {t(f'page.{page}.title', page)}"
                if page == st.session_state.page:
                    st.sidebar.markdown(f'<div class="cip-nav-active">{safe_html(label)}</div>', unsafe_allow_html=True)
                if st.sidebar.button(label, key=f"nav_{page}", use_container_width=True):
                    st.session_state.page = page
                    st.rerun()


def auth_screen():
    st.markdown(f'<div class="cip-hero"><span class="cip-pill">{safe_html(t("app.name"))}</span><h1>{safe_html("Review contracts with evidence, risk, and clarity." if not is_rtl() else "راجع العقود بالأدلة والمخاطر والوضوح.")}</h1><p class="cip-muted">{safe_html("Secure Streamlit MVP backed by FastAPI, MongoDB, and grounded analysis." if not is_rtl() else "واجهة Streamlit آمنة مدعومة بـ FastAPI و MongoDB وتحليل قائم على الأدلة.")}</p></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.05, 1])
    with col2:
        st.write("")
        mode = st.radio("Account action", ["Sign In", "Create Account"], horizontal=True, label_visibility="collapsed")
        st.session_state.auth_mode = "register" if mode == "Create Account" else "login"
        st.markdown('<div class="cip-auth-card">', unsafe_allow_html=True)
        with st.container():
            if st.session_state.auth_mode == "register":
                st.header("Create account" if not is_rtl() else "إنشاء حساب")
                with st.form("register_form"):
                    full_name = st.text_input("Full name" if not is_rtl() else "الاسم الكامل", autocomplete="name")
                    email = st.text_input("Email" if not is_rtl() else "البريد الإلكتروني", autocomplete="email")
                    password = st.text_input("Password" if not is_rtl() else "كلمة المرور", type="password", autocomplete="new-password")
                    confirm = st.text_input("Confirm password" if not is_rtl() else "تأكيد كلمة المرور", type="password", autocomplete="new-password")
                    submitted = st.form_submit_button("Create account" if not is_rtl() else "إنشاء حساب", use_container_width=True)
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
                st.header("Log in" if not is_rtl() else "تسجيل الدخول")
                with st.form("login_form"):
                    email = st.text_input("Email" if not is_rtl() else "البريد الإلكتروني", autocomplete="email")
                    password = st.text_input("Password" if not is_rtl() else "كلمة المرور", type="password", autocomplete="current-password")
                    submitted = st.form_submit_button("Log in" if not is_rtl() else "تسجيل الدخول", use_container_width=True)
                if submitted:
                    if not email or not password:
                        st.error("Email and password are required.")
                    else:
                        with st.spinner("Signing in..."):
                            ok, data = api_request("POST", "/auth/login", json={"email": email, "password": password})
                        if ok:
                            st.session_state.token = data["access_token"]
                            st.session_state.user = data["user"]
                            apply_user_preferences(st.session_state.user)
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
    render_page_header("Home")
    ok_c, clients = api_request("GET", "/clients")
    ok_k, contracts = api_request("GET", "/contracts")
    c1,c2,c3 = st.columns(3)
    c1.metric("Clients", len(clients) if ok_c else 0)
    c2.metric("Contracts", len(contracts) if ok_k else 0)
    c3.metric("Review status", "Ready")
    st.info(t("home.help"))


def clients_page():
    render_page_header("Clients", t("action.create_client"))
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
        for client in data:
            st.markdown(f'<div class="cip-card"><div class="cip-card-header"><h4>{safe_html(client.get("name", "Client"))}</h4><span class="cip-badge cip-badge-blue">{safe_html(client.get("industry", "General"))}</span></div><p>{safe_html(client.get("notes", "No notes yet."))}</p></div>', unsafe_allow_html=True)
    else:
        render_empty_state(t("page.Clients.title"), t("empty.clients"))


def contracts_page():
    render_page_header("Contracts", t("action.upload_contract"))
    ok, clients = api_request("GET", "/clients")
    client_options = {c["name"]: c["id"] for c in clients} if ok else {}
    with st.form("upload_form"):
        name = st.text_input("Contract name")
        client_name = st.selectbox("Client", ["No client"] + list(client_options.keys()))
        file = st.file_uploader("Upload PDF, DOCX, TXT, PNG, JPG, or JPEG", type=["pdf", "docx", "txt", "png", "jpg", "jpeg"])
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
        for contract in contracts:
            cid = safe_text(contract.get("id") or contract.get("_id"), "")
            st.markdown(f'<div class="cip-card"><div class="cip-card-header"><h4>{safe_html(contract.get("name") or contract.get("filename") or "Untitled contract")}</h4><span class="cip-badge cip-badge-blue">{safe_html(cid[:8])}</span></div><p><strong>File:</strong> {safe_html(contract.get("filename", "Uploaded contract"))}</p><p class="cip-muted">Use Contract Analysis, Chat, or Benchmark to review this document.</p></div>', unsafe_allow_html=True)
    else:
        render_empty_state(t("page.Contracts.title"), t("empty.contracts"))


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
    render_page_header("Contract Analysis", t("action.run_analysis"))
    selected_label, cid = select_contract()
    if not cid:
        return
    endpoint_path = f"/contracts/{cid}/analyze?explanation_language={effective_explanation_language()}&ui_language={st.session_state.language}"
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
            st.session_state.analysis_report_pdf = None
            st.session_state.analysis_report_filename = None
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
        st.markdown("### Download Report")
        if st.button("Download PDF Report", use_container_width=True):
            with st.spinner("Generating PDF report..."):
                ok_pdf, pdf_data, pdf_filename = api_download(f"/contracts/{cid}/analysis/report?report_language={effective_report_language()}", timeout=120)
            if ok_pdf:
                st.session_state.analysis_report_pdf = pdf_data
                st.session_state.analysis_report_filename = pdf_filename or f"contract-intelligence-report-{datetime.now().strftime('%Y%m%d')}.pdf"
                st.success("PDF report is ready to download.")
            else:
                st.error(user_message(pdf_data))
        if st.session_state.get("analysis_report_pdf"):
            st.download_button("Save PDF Report", data=st.session_state.analysis_report_pdf, file_name=st.session_state.get("analysis_report_filename", "contract-intelligence-report.pdf"), mime="application/pdf", use_container_width=True)
    else:
        st.info("Run analysis first to generate a report and see health score, risks, clauses, recommendations, and evidence trace.")


def chat_page():
    render_page_header("Contract Chat", t("action.new_chat"))
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
            ok, data = api_request("POST", endpoint_path, json={"question": prompt, "explanation_language": effective_explanation_language()}, timeout=120)
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
                model_used=data.get("model_used"),
                response_language=data.get("response_language"),
                explanation_language=data.get("explanation_language"),
                raw=data,
            )
            st.rerun()
        else:
            st.markdown(f'<div class="cip-error-card"><strong>I could not complete the chat request.</strong><br>{safe_html(user_message(data))}</div>', unsafe_allow_html=True)
    with st.expander("Advanced / Debug Output", expanded=False):
        st.caption("Last chat/API debug details")
        st.json({"contract_id": cid, "contract_label": selected_label, "last_api_debug": st.session_state.last_api_debug, "last_assistant_raw": next((m.get("raw") for m in reversed(st.session_state.chat_history) if m.get("role") == "assistant"), None)})


def benchmark_page():
    render_page_header("Benchmark", t("action.run_benchmark"))
    selected_label, cid = select_contract()
    if not cid:
        return
    st.markdown(f'<div class="cip-chat-contract">Selected contract: <strong>{safe_html(selected_label)}</strong></div>', unsafe_allow_html=True)
    if st.button("Run benchmark", use_container_width=True):
        with st.spinner("Comparing against illustrative benchmark profiles..."):
            ok, data = api_request("POST", f"/contracts/{cid}/benchmark?explanation_language={effective_explanation_language()}", timeout=90)
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
    render_page_header("Settings / System Health")
    health = health_marker()
    ok_diag, diagnostics = api_request("GET", "/system/diagnostics", timeout=15)
    if not ok_diag:
        diagnostics = {}
    backend_ok = health.get("Backend Build") not in {None, "unreachable"}
    mongo_ok = health.get("mongodb_status") == "connected"
    auth_ok = health.get("auth_status") == "enabled"
    llm_ok = bool(health.get("llm_reachable"))
    degraded = backend_ok and mongo_ok and auth_ok and not llm_ok
    overall = service_status_label(backend_ok and mongo_ok and auth_ok, degraded)
    if overall == "Healthy":
        explanation = "Frontend, backend, database, authentication, and AI model are reachable."
    elif overall == "Degraded":
        explanation = "Core app services are available, but AI/Ollama is unavailable so fallback mode may be used."
    else:
        explanation = "One or more core services are unavailable. Review the cards and troubleshooting guidance below."
    render_status_card("Overall System Status", overall, f"System Status: {overall}", explanation, health.get("timestamp", "Now"))

    st.markdown("### Service Status")
    cols = st.columns(3)
    with cols[0]:
        render_status_card("Frontend", "Healthy", FRONTEND_BUILD, "Streamlit active frontend is rendering this dashboard.")
    with cols[1]:
        render_status_card("Backend API", "Healthy" if backend_ok else "Offline", health.get("Backend Build", "unreachable"), "FastAPI health endpoint is reachable." if backend_ok else "FastAPI health endpoint is not reachable.")
    with cols[2]:
        render_status_card("MongoDB", "Healthy" if mongo_ok else "Offline", health.get("mongodb_status", "unknown"), "Database connection is available." if mongo_ok else "MongoDB is not connected.")
    cols = st.columns(3)
    with cols[0]:
        render_status_card("Authentication", "Healthy" if auth_ok else "Offline", health.get("auth_status", "unknown"), "JWT authentication is enabled." if auth_ok else "Authentication is not healthy.")
    with cols[1]:
        render_status_card("Ollama / LLM", "Healthy" if llm_ok else "Degraded", health.get("llm_ollama_status", "unknown"), "AI analysis and chat should be available." if llm_ok else "LLM unavailable; rule-based fallback will be used.")
    with cols[2]:
        render_status_card("Active Model", "Healthy" if health.get("active_model") else "Degraded", health.get("active_model", "unknown"), "Configured model used for AI analysis and chat.")

    st.markdown("### AI Model Diagnostics")
    llm_debug = diagnostics.get("llm_debug", {}) if isinstance(diagnostics, dict) else {}
    cols = st.columns(4)
    with cols[0]:
        render_metric_card("Active Model", health.get("active_model", "unknown"), "Ollama")
    with cols[1]:
        render_metric_card("LLM Reachable", health.get("llm_reachable", False), health.get("llm_ollama_status", "unknown"))
    with cols[2]:
        mode = "Hybrid AI + rule-based" if llm_ok else "Rule-based fallback"
        render_metric_card("Analysis Mode", mode, "Current AI mode")
    with cols[3]:
        render_metric_card("Avg Response", llm_debug.get("average_response_time_ms", "Not measured"), "milliseconds")
    if st.button("Test AI Model", use_container_width=True):
        with st.spinner("Testing active AI model..."):
            ok_test, test_result = api_request("POST", "/llm/test", timeout=45)
        if ok_test and test_result.get("ok"):
            st.success(f"AI model responded successfully using {test_result.get('model')} in {test_result.get('response_time_ms')} ms.")
        else:
            st.warning(user_message(test_result))
    st.markdown("### AI Prompt / Parser Health")
    parser_cols = st.columns(4)
    with parser_cols[0]:
        render_metric_card("Last LLM Call", llm_debug.get("last_call_successful", "No calls yet"), "yes/no")
    with parser_cols[1]:
        render_metric_card("JSON Parse", llm_debug.get("last_json_parse_successful", "No parses yet"), "yes/no")
    with parser_cols[2]:
        render_metric_card("Fallback Used", llm_debug.get("fallback_used", "Unknown"), llm_debug.get("last_fallback_reason", "No fallback reason"))
    with parser_cols[3]:
        render_metric_card("Prompt Mode", llm_debug.get("last_prompt_mode", "Not recorded"), "analysis / chat / benchmark")
    if llm_ok and llm_debug.get("fallback_used"):
        st.warning("The model is connected. Check the LLM prompt, response parser, and fallback logic in the analysis service.")

    st.markdown("### Backend Endpoint Checks")
    if st.button("Run endpoint checks", use_container_width=True):
        st.session_state.endpoint_checks = run_endpoint_checks()
    for check in st.session_state.get("endpoint_checks", []):
        endpoint_status_row(check["name"], check["status"], check["status_code"], check["explanation"])
    if not st.session_state.get("endpoint_checks"):
        st.info("Run endpoint checks to test health, auth, client, contract, and LLM endpoints. Contract action endpoints are skipped if no contract is available.")

    st.markdown("### Database Stats")
    counts = diagnostics.get("collection_counts", {}) if isinstance(diagnostics, dict) else {}
    count_cols = st.columns(6)
    for idx, name in enumerate(["users", "clients", "contracts", "analyses", "chat_sessions", "benchmarks"]):
        with count_cols[idx]:
            render_metric_card(titleize(name), counts.get(name, "—"), "safe count")

    st.markdown("### Build and Runtime Details")
    cols = st.columns(4)
    with cols[0]:
        render_metric_card("Frontend Build", FRONTEND_BUILD, f"Streamlit {getattr(st, '__version__', 'unknown')}")
    with cols[1]:
        render_metric_card("Backend Build", health.get("Backend Build", "unknown"), f"Python {diagnostics.get('python_version', 'unknown')}")
    with cols[2]:
        render_metric_card("FastAPI", diagnostics.get("fastapi_version", "unknown"), "backend runtime")
    with cols[3]:
        render_metric_card("Docker Mode", diagnostics.get("docker_mode_detected", "unknown"), "container detected")
    st.info("Internal API URL: http://backend:8000. Browser backend URL: http://localhost:8000. The Streamlit container uses the internal Docker URL to reach FastAPI. Your browser uses localhost.")

    st.markdown("### Environment / Config Checks")
    checks = diagnostics.get("config_checks", {}) if isinstance(diagnostics, dict) else {}
    for label, value in checks.items():
        endpoint_status_row(titleize(label), "Healthy" if value else "Failed", "configured" if value else "missing", "Secret values are intentionally hidden.")

    st.markdown("### Recent Safe Errors")
    errors = diagnostics.get("recent_safe_errors", {}) if isinstance(diagnostics, dict) else {}
    if errors:
        for name, value in errors.items():
            render_status_card(titleize(name), "Degraded" if value else "Healthy", value or "No recent safe error", "User-safe error summary only.")
    else:
        st.caption("No recent safe errors are available.")

    st.markdown("### Troubleshooting")
    if not backend_ok:
        st.error("FastAPI is not reachable. Run docker compose up and confirm backend is on port 8000.")
    elif not mongo_ok:
        st.error("MongoDB is unavailable. Check the mongodb container.")
    elif not llm_ok:
        st.warning("Ollama is not reachable. Confirm Ollama is running and the model is pulled.")
    elif llm_debug.get("fallback_used"):
        st.warning("The model is connected. Check the LLM prompt, response parser, and fallback logic in the analysis service.")
    else:
        st.success("No major troubleshooting action is currently required.")

    with st.expander("Advanced / Raw Health Response", expanded=False):
        st.json(health)
    with st.expander("Advanced / LLM Debug", expanded=False):
        st.json(llm_debug)
    with st.expander("Advanced / Endpoint Test Results", expanded=False):
        st.json(st.session_state.get("endpoint_checks", []))
    with st.expander("Advanced / Environment Debug", expanded=False):
        st.json({"diagnostics": diagnostics, "api_base_url": API_BASE_URL})


def main():
    init_state()
    render_global_css()
    render_sidebar()
    if not require_auth():
        auth_screen()
        return
    {"Home": home, "Clients": clients_page, "Contracts": contracts_page, "Contract Analysis": analysis_page, "Contract Chat": chat_page, "Benchmark": benchmark_page, "Settings / System Health": settings_page}[st.session_state.page]()

if __name__ == "__main__":
    main()
