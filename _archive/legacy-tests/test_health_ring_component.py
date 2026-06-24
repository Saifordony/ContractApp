from frontend.components.health_ring import health_ring, health_ring_color


def test_health_ring_renders_html():
    html = health_ring(75)
    assert isinstance(html, str)
    assert html.strip()
    assert "<svg" in html
    assert "75" in html


def test_health_ring_color_green_above_75():
    assert health_ring_color(80) == "#22D68F"
    assert "#22D68F" in health_ring(80)


def test_health_ring_color_amber_50_74():
    assert health_ring_color(60) == "#F59E0B"
    assert "#F59E0B" in health_ring(60)


def test_health_ring_color_red_below_50():
    assert health_ring_color(30) == "#EF4444"
    assert "#EF4444" in health_ring(30)


def test_health_ring_clamps_out_of_range_scores():
    # Score text element shows the clamped value (100), never the raw 120.
    assert ">100</text>" in health_ring(120)
    assert ">120</text>" not in health_ring(120)
    assert ">0</text>" in health_ring(-10)
