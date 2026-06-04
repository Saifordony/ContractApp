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
    for label in ["Dashboard", "Clients", "Contracts", "Analyze", "Benchmark", "AI Assistant", "Settings"]:
        assert f'"{label}"' in source
    assert "Contract Readiness Review" not in source[source.index("nav_items = ["):source.index("navigation = st.radio")]
