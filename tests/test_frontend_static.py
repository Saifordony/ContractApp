from pathlib import Path


def test_clause_card_does_not_nest_streamlit_expanders():
    source = Path("frontend/components/clause_cards.py").read_text()
    assert source.count("st.expander(") == 1
    assert "st.expander(\"Evidence snippets\")" not in source
    assert "#### Evidence snippets" in source


def test_contract_analysis_uses_shared_clause_card_renderer():
    source = Path("frontend/streamlit_app.py").read_text()
    assert "render_clause_card(clause_type, payload" in source
