"""Shared auth/session helpers for the multipage app.

`decode_jwt_exp` is dependency-free (manual base64 decode, no signature check) so
it can power the session-expiry countdown and be unit-tested in isolation.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Optional

import streamlit as st


def decode_jwt_exp(token: str) -> Optional[int]:
    """Read the ``exp`` claim from a JWT without verifying its signature.

    Returns the expiry as a unix timestamp, or ``None`` if it cannot be read.
    """
    try:
        payload_segment = token.split(".")[1]
        padding = "=" * (-len(payload_segment) % 4)
        decoded = base64.urlsafe_b64decode(payload_segment + padding)
        claims = json.loads(decoded)
        exp = claims.get("exp")
        return int(exp) if exp is not None else None
    except Exception:
        return None


def seconds_until_expiry(token: str, *, now: Optional[float] = None) -> Optional[float]:
    """Seconds remaining until the token expires (negative if already expired)."""
    exp = decode_jwt_exp(token)
    if exp is None:
        return None
    return exp - (time.time() if now is None else now)


def is_authenticated() -> bool:
    try:
        return bool(st.session_state.get("token"))
    except Exception:
        return False


def save_token(token: str, username: str = "") -> None:
    st.session_state["token"] = token
    if username:
        st.session_state["username"] = username


def clear_session() -> None:
    for key in ("token", "username"):
        if key in st.session_state:
            del st.session_state[key]


def require_auth() -> None:
    """Stop rendering the current page unless the user is signed in.

    Pages call this at the top. Degrades gracefully if session state is empty.
    """
    if not is_authenticated():
        st.warning("Please sign in to continue.")
        st.info("Open the main app page to sign in, then return here.")
        st.stop()
    render_session_timer()


def render_session_timer() -> None:
    """Show a countdown when the session is close to expiring; log out if expired."""
    token = st.session_state.get("token", "") if hasattr(st, "session_state") else ""
    if not token:
        return
    remaining = seconds_until_expiry(token)
    if remaining is None:
        return
    if remaining < 0:
        clear_session()
        st.warning("Your session has expired. Please sign in again.")
        st.stop()
    if remaining < 300:
        minutes, seconds = divmod(int(remaining), 60)
        st.warning(f"⚠️ Session expires in {minutes}:{seconds:02d} — save your work")
