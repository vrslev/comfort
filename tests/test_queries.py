from comfort.queries import _format_weight, format_money


def test_format_money():
    assert format_money("1") == "1 ₽"
    assert format_money(1) == "1 ₽"
    assert format_money(1.0) == "1 ₽"


def test_format_weight():
    assert _format_weight(1) == "1.0 кг"
    assert _format_weight(1.0) == "1.0 кг"
