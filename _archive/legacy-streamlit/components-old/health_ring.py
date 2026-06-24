"""Animated circular SVG progress ring for the contract health score."""

from __future__ import annotations

import streamlit as st

# Design-system colours (kept inline so the ring renders correctly even before
# the global CSS redesign is applied).
_SUCCESS = "#22D68F"
_WARNING = "#F59E0B"
_DANGER = "#EF4444"
_TRACK = "#344263"
_MUTED = "#6B7A99"

# Geometry: radius 52 -> circumference = 2 * pi * 52 ≈ 326.7.
_RADIUS = 52
_CIRCUMFERENCE = 326.7


def health_ring_color(score: int) -> str:
    """Return the arc colour for a score: green >= 75, amber 50–74, red < 50."""
    if score >= 75:
        return _SUCCESS
    if score >= 50:
        return _WARNING
    return _DANGER


def health_ring(score: int, label: str = "Health Score") -> str:
    """Render an animated SVG circular progress ring for the health score.

    ``score`` is clamped to 0–100.  The component renders via
    ``st.markdown(..., unsafe_allow_html=True)`` and also returns the HTML
    string so it can be embedded elsewhere or asserted against in tests.
    """
    try:
        numeric = int(round(float(score)))
    except (TypeError, ValueError):
        numeric = 0
    numeric = max(0, min(100, numeric))

    color = health_ring_color(numeric)
    # Fraction of the circumference left undrawn (the "empty" part of the ring).
    dash_offset = round(_CIRCUMFERENCE * (1 - numeric / 100), 2)
    # Unique keyframe name so multiple rings on a page animate independently.
    anim = f"ring-draw-{numeric}-{abs(hash(label)) % 10000}"

    html = f"""
    <div class="health-ring" style="display:flex;flex-direction:column;align-items:center;gap:0.35rem;">
      <style>
        @keyframes {anim} {{
          from {{ stroke-dashoffset: {_CIRCUMFERENCE}; }}
          to {{ stroke-dashoffset: {dash_offset}; }}
        }}
      </style>
      <svg width="140" height="140" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="{_RADIUS}" fill="none" stroke="{_TRACK}" stroke-width="10" />
        <circle cx="60" cy="60" r="{_RADIUS}" fill="none" stroke="{color}" stroke-width="10"
                stroke-linecap="round"
                stroke-dasharray="{_CIRCUMFERENCE}"
                stroke-dashoffset="{dash_offset}"
                transform="rotate(-90 60 60)"
                style="animation: {anim} 1.1s ease-out forwards;" />
        <text x="60" y="60" text-anchor="middle" dominant-baseline="central"
              font-family="'Playfair Display', Georgia, serif" font-size="30"
              font-weight="700" fill="{color}">{numeric}</text>
      </svg>
      <div class="health-ring-label"
           style="font-family:'DM Sans',sans-serif;color:{_MUTED};font-size:0.85rem;letter-spacing:0.02em;">
        {label}
      </div>
    </div>
    """

    try:
        st.markdown(html, unsafe_allow_html=True)
    except Exception:
        # Rendering is a side effect; callers/tests may use the returned HTML.
        pass
    return html
