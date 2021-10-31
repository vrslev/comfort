from comfort.queries import _format_weight


def test_format_weight():
    assert _format_weight(1) == "1.0 кг"
    assert _format_weight(1.0) == "1.0 кг"
