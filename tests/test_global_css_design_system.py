"""Static checks for the redesigned premium design-system CSS (Dimension 2.1)."""

import inspect

from frontend.styles import global_css


def test_premium_component_classes_present():
    css = inspect.getsource(global_css.apply_premium_components_css)
    for cls in [
        ".stat-card",
        ".clause-card.found",
        ".clause-card.missing",
        ".clause-card.low-confidence",
        ".confidence-badge",
        ".confidence-high",
        ".evidence-quote",
        ".chat-bubble.user",
    ]:
        assert cls in css, f"missing class {cls}"


def test_design_tokens_and_fonts_present():
    css = inspect.getsource(global_css.apply_premium_components_css)
    for token in ["--accent-2", "--accent-3", "--glow-blue", "--radius-md", "--shadow-md"]:
        assert token in css
    assert "DM+Sans" in css
    assert "DM+Mono" in css
    assert "Playfair+Display" in css
    assert "fadeInUp" in css


def test_base_tokens_preserved_for_theme_switcher():
    # The base theme tokens the app and existing tests rely on must remain.
    css = inspect.getsource(global_css.apply_global_css)
    for token in ["--bg", "--surface", "--text", "--muted", "--primary", "--border", "--success", "--warning", "--danger"]:
        assert token in css
