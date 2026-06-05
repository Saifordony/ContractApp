from pathlib import Path


def test_clause_card_does_not_nest_streamlit_expanders():
    source = Path("frontend/components/clause_cards.py").read_text()
    assert source.count("st.expander(") == 1
    assert "st.expander(\"Evidence snippets\")" not in source
    assert "#### Evidence snippets" in source


def test_contract_analysis_uses_shared_clause_card_renderer():
    source = Path("frontend/streamlit_app.py").read_text()
    assert "render_clause_card(clause_type, payload" in source


def test_auth_page_uses_contract_intelligence_brand_and_workspace_copy():
    source = Path("frontend/streamlit_app.py").read_text()
    assert "Contract Intelligence" in source
    assert "Create your workspace" in source
    assert "Start analyzing contracts with AI-powered insights." in source
    assert "Create account" in source
    assert "Passwords do not match" in source


def test_sidebar_uses_business_friendly_navigation_labels():
    source = Path("frontend/streamlit_app.py").read_text()
    for label in [
        "Dashboard",
        "Demo Mode",
        "Presentation Mode",
        "Clients",
        "Contracts",
        "Analyze",
        "Benchmark",
        "AI Assistant",
        "Security & Privacy",
        "Settings",
    ]:
        assert f'"{label}"' in source
    assert "Contract Readiness Review" not in source[source.index("nav_items = ["):source.index("navigation = st.radio")]


def test_demo_mode_contains_preloaded_grading_workspace():
    source = Path("frontend/streamlit_app.py").read_text()
    assert "DEMO_CLIENT_NAME" in source
    assert "Atlas Engineering LLC" in source
    assert "Load Demo Workspace" in source
    assert "Two-minute grading demo script" in source
    assert "Download Demo PDF Report" in source


def test_presentation_and_security_pages_are_available():
    source = Path("frontend/streamlit_app.py").read_text()
    assert "def presentation_mode_page" in source
    assert "problem, solution, AI pipeline, architecture" in source
    assert "def security_privacy_page" in source
    assert "processed by your local model configuration" in source
    assert "Not legal advice" in source


def test_dashboard_includes_guided_onboarding():
    source = Path("frontend/streamlit_app.py").read_text()
    assert "def render_guided_onboarding" in source
    assert "Create client" in source
    assert "Upload contract" in source
    assert "Run analysis" in source
    assert "render_guided_onboarding()" in source
