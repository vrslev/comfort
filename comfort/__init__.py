from collections import Counter, defaultdict
from typing import Any, Iterable

__version__ = "0.2.0"


def count_quantity(
    data: Iterable[dict[Any, Any]], key_key: str = "item_code", value_key: str = "qty"
):
    c: Counter[str, int] = Counter()
    for item in data:
        c[item[key_key]] += item[value_key]
    return c


def search_by_id(data: Iterable[dict[Any, Any]], id_key: str) -> dict[Any, Any]:
    d = defaultdict(list)
    for item in data:
        d[item[id_key]].append(item)
    return dict(d)  # type: ignore
