from __future__ import annotations


def titleize_key(value: str | None) -> str:
    if not value:
        return "Not Available"
    return str(value).replace("_", " ").replace("/", " / ").title()


def status_label(value: str | None) -> str:
    mapping = {
        "found": "Found",
        "partial": "Partially Found",
        "partially_found": "Partially Found",
        "needs_review": "Needs Review",
        "not_found": "Not Found",
        "missing": "Not Found",
    }
    return mapping.get(str(value or "").lower(), titleize_key(value))


def truncate_middle(text: str, length: int = 140) -> str:
    text = str(text or "")
    if len(text) <= length:
        return text
    return text[: length - 1] + "…"
