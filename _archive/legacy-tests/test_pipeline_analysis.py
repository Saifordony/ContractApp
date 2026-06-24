from backend.services.pipeline_analysis import analyze_pipeline


def test_weighted_pipeline_math():
    opportunities = [
        {"client": "A", "opportunity_name": "Deal 1", "stage": "proposal", "value": 100000, "last_updated": "2026-02-01T00:00:00+00:00", "owner": "x"},
        {"client": "B", "opportunity_name": "Deal 2", "stage": "negotiation", "value": 50000, "last_updated": "2026-02-10T00:00:00+00:00", "owner": "y"},
    ]
    result = analyze_pipeline(opportunities)
    # proposal=0.5, negotiation=0.7 => 50k + 35k = 85k
    assert result["weighted_pipeline"] == 85000.0
    assert result["total_pipeline"] == 150000.0


def test_pipeline_detects_stale_deals():
    opportunities = [
        {"client": "A", "opportunity_name": "Old Deal", "stage": "qualification", "value": 1000, "last_updated": "2020-01-01T00:00:00+00:00", "owner": "owner"},
    ]
    result = analyze_pipeline(opportunities)
    assert result["velocity"]["stale_deals_over_30_days"] >= 1
    assert result["stale_deals"]
