from collections import Counter, defaultdict
from typing import Any, Iterable

__version__ = "0.2.0"


def count_quantity(
    data: Iterable[Any], key_key: str = "item_code", value_key: str = "qty"
):
    c: Counter[str] = Counter()
    for item in data:
        c[getattr(item, key_key)] += getattr(item, value_key)
    return c


def group_by_key(
    data: Iterable[dict[Any, Any]], key: str = "item_code"
) -> dict[Any, Any]:
    d: dict[str, list[Any]] = defaultdict(list[Any])
    for item in data:
        d[getattr(item, key)].append(item)
    return dict(d)  # type: ignore
