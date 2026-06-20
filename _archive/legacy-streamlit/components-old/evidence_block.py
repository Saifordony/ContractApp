"""Render AI evidence snippets as styled contract-quote cards."""

from __future__ import annotations

from typing import List

import streamlit as st

_ACCENT = "#4F7FEF"
_PRIMARY = "#D4E2FF"
_MUTED = "#6B7A99"


def evidence_quote_html(quote: str, location: str = "") -> str:
    """Build the HTML for a single styled evidence quote with a location label."""
    quote = (quote or "").strip()
    location = (location or "").strip()
    location_html = (
        f"<div style=\"font-family:'DM Sans',sans-serif;color:{_MUTED};"
        f"font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em;"
        f"margin-bottom:0.25rem;\">{location}</div>"
        if location
        else ""
    )
    return (
        f"<div class='evidence-quote' style=\"background:rgba(79,127,239,0.08);"
        f"border-left:3px solid {_ACCENT};border-radius:0 8px 8px 0;"
        f"padding:0.75rem 1rem;font-family:'DM Mono',monospace;font-size:0.85rem;"
        f"color:{_PRIMARY};margin:0.5rem 0;line-height:1.6;\">"
        f"{location_html}{quote}</div>"
    )


def evidence_block(snippets: List[dict], title: str = "Evidence from Contract") -> None:
    """Render ``evidence_snippets`` from an AI response as styled quote cards.

    Each snippet is a dict with ``quote`` and ``location`` keys.  When there are
    more than 3 snippets the list collapses into an expander to keep the page tidy.
    """
    snippets = [s for s in (snippets or []) if isinstance(s, dict) and s.get("quote")]
    if not snippets:
        return

    def _render() -> None:
        for snippet in snippets:
            st.markdown(
                evidence_quote_html(str(snippet.get("quote", "")), str(snippet.get("location", ""))),
                unsafe_allow_html=True,
            )

    if len(snippets) > 3:
        with st.expander(f"{title} ({len(snippets)})"):
            _render()
    else:
        st.markdown(f"**{title}**")
        _render()
