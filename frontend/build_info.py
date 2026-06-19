"""Frontend build marker.

Rendered in the sidebar footer on every page. If you edit frontend code and the
value shown in the browser does not match what's here, the running Streamlit
process is serving stale code (wrong working directory, a baked Docker image with
no bind mount, or the file watcher not firing) -- not a code bug. Bump this string
to confirm the edit->reload loop end to end.
"""

APP_BUILD = "2026-06-19 · dev-loop verified"
