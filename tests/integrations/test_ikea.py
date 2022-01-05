from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import ikea_api.wrappers
import pytest
import sentry_sdk
from ikea_api import IKEA
from ikea_api.exceptions import (
    GraphQLError,
    IKEAAPIError,
    NoDeliveryOptionsAvailableError,
    OrderCaptureError,
)
from ikea_api.wrappers.types import GetDeliveryServicesResponse, ParsedItem

import comfort.integrations.ikea
import frappe
from comfort import count_qty, counters_are_same, get_all, get_doc, get_value
from comfort.comfort_core.doctype.ikea_settings.ikea_settings import (
    IkeaSettings,
    get_authorized_api,
    get_guest_api,
)
from comfort.entities.doctype.item.item import Item
from comfort.entities.doctype.item_category.item_category import ItemCategory
from comfort.integrations.ikea import (
    FetchItemsResult,
    _create_item,
    _create_item_categories,
    _fetch_child_items,
    _get_items_to_fetch,
    _make_item_category,
    _make_items_from_child_items_if_not_exist,
    add_items_to_cart,
    fetch_items,
    get_delivery_services,
    get_items,
    get_purchase_history,
    get_purchase_info,
)
from frappe.exceptions import ValidationError
from tests.conftest import (
    mock_delivery_services,
    mock_purchase_history,
    patch_get_delivery_services,
)

# TODO: Remove redundant parts of tests


@pytest.mark.usefixtures("ikea_settings")
def test_get_delivery_services_no_items():
    with pytest.raises(
        ValidationError, match="No items selected to check delivery services"
    ):
        get_delivery_services({})


def test_get_delivery_services_no_zip_code(ikea_settings: IkeaSettings):
    ikea_settings.zip_code = None
    ikea_settings.save()
    with pytest.raises(ValidationError, match="Enter Zip Code in Ikea Settings"):
        get_delivery_services({"14251253": 1})


@pytest.mark.usefixtures("ikea_settings")
def test_get_delivery_services_ok(monkeypatch: pytest.MonkeyPatch):
    patch_get_delivery_services(monkeypatch)
    assert get_delivery_services({"14251253": 1}) == mock_delivery_services


def test_get_delivery_services_no_delivery_options_raises(
    monkeypatch: pytest.MonkeyPatch, ikea_settings: IkeaSettings
):
    def new_mock_delivery_services(api: IKEA, items: Any, zip_code: Any):
        assert api.token == get_guest_api().token
        assert zip_code == ikea_settings.zip_code
        raise NoDeliveryOptionsAvailableError(Mock())

    frappe.message_log = []

    monkeypatch.setattr(
        ikea_api.wrappers, "get_delivery_services", new_mock_delivery_services
    )

    assert get_delivery_services({"14251253": 1}) is None
    assert "No available delivery options" in str(frappe.message_log)  # type: ignore


def test_get_delivery_services_no_delivery_options_empty(
    monkeypatch: pytest.MonkeyPatch, ikea_settings: IkeaSettings
):
    def new_mock_delivery_services(api: IKEA, items: Any, zip_code: Any):
        assert api.token == get_guest_api().token
        assert zip_code == ikea_settings.zip_code
        return GetDeliveryServicesResponse(delivery_options=[], cannot_add=[])

    frappe.message_log = []

    monkeypatch.setattr(
        ikea_api.wrappers, "get_delivery_services", new_mock_delivery_services
    )

    assert get_delivery_services({"14251253": 1}) is None
    assert "No available delivery options" in str(frappe.message_log)  # type: ignore


def test_get_delivery_services_all_delivery_options_unavailable(
    monkeypatch: pytest.MonkeyPatch, ikea_settings: IkeaSettings
):
    def new_mock_delivery_services(api: IKEA, items: Any, zip_code: Any):
        return SimpleNamespace(
            delivery_options=[
                SimpleNamespace(is_available=False),
                SimpleNamespace(is_available=False),
            ],
            cannot_add=[],
        )

    frappe.message_log = []

    monkeypatch.setattr(
        ikea_api.wrappers, "get_delivery_services", new_mock_delivery_services
    )

    assert get_delivery_services({"14251253": 1}) is None
    assert "No available delivery options" in str(frappe.message_log)  # type: ignore


def test_get_delivery_services_some_delivery_options_available(
    monkeypatch: pytest.MonkeyPatch, ikea_settings: IkeaSettings
):
    exp_res = SimpleNamespace(
        delivery_options=[
            SimpleNamespace(is_available=False),
            SimpleNamespace(is_available=True),
        ],
        cannot_add=[],
    )

    def new_mock_delivery_services(api: IKEA, items: Any, zip_code: Any):
        return deepcopy(exp_res)

    frappe.message_log = []

    monkeypatch.setattr(
        ikea_api.wrappers, "get_delivery_services", new_mock_delivery_services
    )

    assert get_delivery_services({"14251253": 1}) == exp_res
    assert "No available delivery options" not in str(frappe.message_log)  # type: ignore


@pytest.mark.parametrize(
    "message",
    (
        "Error while connecting to ISOM",
        "Error while connecting to SPE",
        "Cannot read property 'get' of undefined",
    ),
)
def test_get_delivery_services_internal_ikea_error(
    monkeypatch: pytest.MonkeyPatch, ikea_settings: IkeaSettings, message: str
):
    class MockResponse:
        status_code = 200
        text = json.dumps({"message": message})
        _json = {"message": message}

    def new_mock_delivery_services(api: IKEA, items: Any, zip_code: Any):
        assert api.token == get_guest_api().token
        assert zip_code == ikea_settings.zip_code
        raise OrderCaptureError(MockResponse())  # type: ignore

    monkeypatch.setattr(
        ikea_api.wrappers, "get_delivery_services", new_mock_delivery_services
    )
    assert get_delivery_services({"14251253": 1}) is None
    assert "Internal IKEA error, try again" in str(frappe.message_log)  # type: ignore


def test_get_delivery_services_ikeaapierror_502(
    monkeypatch: pytest.MonkeyPatch, ikea_settings: IkeaSettings
):
    class MockResponse:
        status_code = 502
        text = "ff"

    def new_mock_delivery_services(api: IKEA, items: Any, zip_code: Any):
        raise IKEAAPIError(MockResponse())  # type: ignore

    monkeypatch.setattr(
        ikea_api.wrappers, "get_delivery_services", new_mock_delivery_services
    )

    assert get_delivery_services({"14251253": 1}) is None
    assert "Internal IKEA error, try again" in str(frappe.message_log)  # type: ignore


def test_get_delivery_services_ikeaapierror_not_502(
    monkeypatch: pytest.MonkeyPatch, ikea_settings: IkeaSettings
):
    class MockResponse:
        status_code = 504
        text = "ff"

    def new_mock_delivery_services(api: IKEA, items: Any, zip_code: Any):
        raise IKEAAPIError(MockResponse())  # type: ignore

    monkeypatch.setattr(
        ikea_api.wrappers, "get_delivery_services", new_mock_delivery_services
    )

    with pytest.raises(IKEAAPIError) as exc:
        get_delivery_services({"14251253": 1})
    assert exc.value.response.status_code == 504
    assert exc.value.response.text == "ff"


def test_get_delivery_services_other_error(
    monkeypatch: pytest.MonkeyPatch, ikea_settings: IkeaSettings
):
    exp_arg = {"message": "some different error"}

    class MockResponse:
        status_code = 200
        text = json.dumps(exp_arg)
        _json = exp_arg

    def new_mock_delivery_services(api: IKEA, items: Any, zip_code: Any):
        assert api.token == get_guest_api().token
        assert zip_code == ikea_settings.zip_code
        raise OrderCaptureError(MockResponse())  # type: ignore

    monkeypatch.setattr(
        ikea_api.wrappers, "get_delivery_services", new_mock_delivery_services
    )
    with pytest.raises(OrderCaptureError, match=json.dumps(exp_arg)):
        assert get_delivery_services({"14251253": 1}) is None


@pytest.mark.parametrize("authorize", (True, False))
@pytest.mark.usefixtures("ikea_settings")
def test_add_items_to_cart_with_items(monkeypatch: pytest.MonkeyPatch, authorize: bool):
    myapi = get_authorized_api() if authorize else get_guest_api()

    def mock_add_items_to_cart(api: IKEA, *, items: Any):
        assert api.token == myapi.token

    monkeypatch.setattr(ikea_api.wrappers, "add_items_to_cart", mock_add_items_to_cart)
    add_items_to_cart({"14251253": 1}, authorize)


@pytest.mark.usefixtures("ikea_settings")
def test_add_items_to_cart_no_items():
    with pytest.raises(ValidationError, match="No items selected to add to cart"):
        add_items_to_cart({}, authorize=False)


@pytest.mark.usefixtures("ikea_settings")
def test_get_purchase_history(monkeypatch: pytest.MonkeyPatch):
    def mock_get_purchase_history(api: IKEA):
        assert api.token == get_authorized_api().token
        return mock_purchase_history

    monkeypatch.setattr(
        ikea_api.wrappers, "get_purchase_history", mock_get_purchase_history
    )
    assert get_purchase_history() == mock_purchase_history


@pytest.mark.parametrize("use_lite_id", (True, False))
@pytest.mark.usefixtures("ikea_settings")
def test_get_purchase_info_main(monkeypatch: pytest.MonkeyPatch, use_lite_id: bool):
    exp_purchase_id = 111111110

    class MockGetPurchaseInfoResult:
        def dict(self):
            pass

    def mock_get_purchase_info(api: IKEA, *, id: str, email: str):
        assert api.token == get_authorized_api().token
        assert id == str(exp_purchase_id)
        if use_lite_id:
            # TODO: Remove this block: IkeaSettings don't store username anymore
            assert email == get_value("Ikea Settings", None, "username")
        else:
            assert email is None
        return MockGetPurchaseInfoResult()

    monkeypatch.setattr(ikea_api.wrappers, "get_purchase_info", mock_get_purchase_info)
    get_purchase_info(exp_purchase_id, use_lite_id)


@pytest.mark.usefixtures("ikea_settings")
def test_get_purchase_info_ikeaapierror_504(monkeypatch: pytest.MonkeyPatch):
    exp_purchase_id = 111111110

    class MockGetPurchaseInfoResult:
        def dict(self):
            return "foo"

    count = 0

    def mock_get_purchase_info(api: IKEA, *, id: str, email: str):
        assert api.token == get_authorized_api().token
        assert id == str(exp_purchase_id)
        assert email is None
        nonlocal count
        if count in (0, 1):
            count += 1
            raise IKEAAPIError(
                SimpleNamespace(  # type: ignore
                    status_code=504,
                    text=(
                        "<html><body><h1>504 Gateway Time-out</h1>\n"
                        + "The server didn't respond in time.\n</body></html>\n"
                    ),
                )
            )
        else:
            return MockGetPurchaseInfoResult()

    monkeypatch.setattr(ikea_api.wrappers, "get_purchase_info", mock_get_purchase_info)
    assert get_purchase_info(exp_purchase_id, False) == "foo"


@pytest.mark.usefixtures("ikea_settings")
def test_get_purchase_info_ikeaapierror_not_504(monkeypatch: pytest.MonkeyPatch):
    exp_purchase_id = 111111110

    class MockGetPurchaseInfoResult:
        def dict(self):
            return "foo"

    count = 0

    def mock_get_purchase_info(api: IKEA, *, id: str, email: str):
        assert api.token == get_authorized_api().token
        assert id == str(exp_purchase_id)
        assert email is None
        nonlocal count
        if count in (0, 1):
            count += 1
            raise IKEAAPIError(SimpleNamespace(status_code=404, text=""))  # type: ignore
        else:
            return MockGetPurchaseInfoResult()

    monkeypatch.setattr(ikea_api.wrappers, "get_purchase_info", mock_get_purchase_info)
    with pytest.raises(IKEAAPIError, match="404"):
        get_purchase_info(exp_purchase_id, False)


@pytest.mark.parametrize("is_dict", (True, False))
@pytest.mark.parametrize(
    ("err", "should_capture"),
    (
        ({"not message": "foo"}, True),
        ({"message": "Purchase not found"}, False),
        ({"message": "Order not found"}, False),
        ({"message": "Invalid order id"}, False),
        ([{"message": "Purchase not found"}], False),
        (
            {
                "message": "Exception while fetching data (/order/id) : null",
                "locations": [{"line": 4, "column": 13}],
                "path": ["order", "id"],
                "extensions": {"classification": "DataFetchingException"},
            },
            False,
        ),
        ({"message": "some other msg"}, True),
    ),
)
@pytest.mark.usefixtures("ikea_settings")
def test_get_purchase_info_raises(
    monkeypatch: pytest.MonkeyPatch,
    is_dict: bool,
    err: dict[str, str],
    should_capture: bool,
):
    if is_dict:
        msg = {"errors": [err]}
    msg = {"errors": err}
    resp = [msg, {}]

    class MockResponse:
        status_code = 200
        _json = resp
        text = json.dumps(resp)

    exc = GraphQLError(MockResponse())  # type: ignore

    class MockPurchases:
        def __init__(self, token: str):
            pass

        def order_info(self, **kwargs: Any):
            raise exc

    called = False

    def mock_capture_exception(exception: Exception):
        assert exception is exc
        nonlocal called
        called = True

    monkeypatch.setattr(ikea_api, "Purchases", MockPurchases)
    monkeypatch.setattr(sentry_sdk, "capture_exception", mock_capture_exception)

    get_purchase_info(1, False)
    if should_capture:
        assert called
    else:
        assert not called


def test_make_item_category_not_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item.category_name, parsed_item.category_url)
    categories = get_all(ItemCategory, ("category_name", "url"))
    assert categories[0].category_name == parsed_item.category_name
    assert categories[0].url == parsed_item.category_url


def test_make_item_category_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item.category_name, parsed_item.category_url)
    _make_item_category(
        parsed_item.category_name, "https://www.ikea.com/ru/ru/cat/-43638"
    )
    categories = get_all(ItemCategory, "url")
    assert categories[0].url == parsed_item.category_url


def test_make_item_category_no_name(parsed_item: ParsedItem):
    _make_item_category(None, parsed_item.category_url)
    categories = get_all(ItemCategory, "url")
    assert len(categories) == 0


def test_make_items_from_child_items_if_not_exist(parsed_item: ParsedItem):
    _make_items_from_child_items_if_not_exist(parsed_item)
    items_in_db = {item.item_code for item in get_all(Item, "item_code")}
    assert len({i.item_code for i in parsed_item.child_items} ^ items_in_db) == 0

    _make_items_from_child_items_if_not_exist(parsed_item)  # test if not exists block
    items_in_db = {item.item_code for item in get_all(Item, "item_code")}
    assert len({i.item_code for i in parsed_item.child_items} ^ items_in_db) == 0


def test_create_item_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item.category_name, parsed_item.category_url)
    _create_item(parsed_item)

    parsed_item.name = "My New Fancy Item Name"
    parsed_item.url = "https://www.ikea.com/ru/ru/p/-s29128563"
    parsed_item.price = 10000253
    parsed_item.category_name = "New category"
    _make_item_category(parsed_item.category_name, parsed_item.category_url)
    _create_item(parsed_item)

    doc = get_doc(Item, parsed_item.item_code)

    assert doc.item_code == parsed_item.item_code
    assert doc.item_name == parsed_item.name
    assert doc.url == parsed_item.url
    assert doc.rate == parsed_item.price
    assert counters_are_same(
        count_qty(doc.child_items), count_qty(parsed_item.child_items)
    )
    assert len(doc.item_categories) == 1
    assert doc.item_categories[0].item_category == parsed_item.category_name


def test_create_item_exists_child_items_changed(parsed_item: ParsedItem):
    _make_item_category(parsed_item.category_name, parsed_item.category_url)
    _create_item(parsed_item)

    parsed_item.child_items.pop()
    _create_item(parsed_item)

    doc = get_doc(Item, parsed_item.item_code)
    assert counters_are_same(
        count_qty(doc.child_items), count_qty(parsed_item.child_items)
    )


def test_create_item_not_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item.category_name, parsed_item.category_url)
    _create_item(parsed_item)
    doc = get_doc(Item, parsed_item.item_code)

    assert doc.item_code == parsed_item.item_code
    assert doc.item_name == parsed_item.name
    assert doc.url == parsed_item.url
    assert doc.rate == parsed_item.price
    assert doc.weight == parsed_item.weight
    assert counters_are_same(
        count_qty(doc.child_items), count_qty(parsed_item.child_items)
    )
    assert len(doc.item_categories) == 1
    assert doc.item_categories[0].item_category == parsed_item.category_name


def test_create_item_not_exists_no_child_items(parsed_item: ParsedItem):
    parsed_item.child_items = []
    _make_item_category(parsed_item.category_name, parsed_item.category_url)
    _create_item(parsed_item)
    doc = get_doc(Item, parsed_item.item_code)

    assert len(doc.child_items) == 0


def test_create_item_not_exists_no_item_category(parsed_item: ParsedItem):
    parsed_item.category_name = ""
    _create_item(parsed_item)
    doc = get_doc(Item, parsed_item.item_code)

    assert len(doc.item_categories) == 0


def test_get_items_to_fetch_force_update():
    res = _get_items_to_fetch(["10014030"], force_update=True)
    assert len(res) == 1


def test_get_items_to_fetch_not_force_update(item: Item):
    item.db_insert()
    res = _get_items_to_fetch([item.item_code], force_update=False)
    assert len(res) == 0


def test_create_item_categories(parsed_item: ParsedItem):
    items = [parsed_item, parsed_item.copy(), parsed_item]
    new_category = "New Category Name"
    items[1].category_name = new_category
    _create_item_categories(items)
    categories_in_db = {c.name for c in get_all(ItemCategory)}
    assert len({new_category, parsed_item.category_name} ^ categories_in_db) == 0


@pytest.mark.parametrize("force_update", (True, False))
def test_fetch_child_items(monkeypatch: pytest.MonkeyPatch, force_update: bool):
    exp_result = "some items"
    exp_child_items = ["1248129", "124812958"]

    def mock_fetch_items(item_codes: list[str], force_update: bool):
        assert item_codes == exp_child_items
        assert force_update == force_update
        return exp_result

    monkeypatch.setattr(comfort.integrations.ikea, "fetch_items", mock_fetch_items)
    assert (
        _fetch_child_items(
            [  # type: ignore
                SimpleNamespace(
                    child_items=[SimpleNamespace(item_code=i) for i in exp_child_items]
                )
            ],
            force_update,
        )
        == exp_result
    )


def test_fetch_items_no_items_to_fetch(monkeypatch: pytest.MonkeyPatch):
    def mock_get_items_to_fetch(item_codes: list[str], force_update: bool) -> list[Any]:
        return []

    monkeypatch.setattr(
        comfort.integrations.ikea, "_get_items_to_fetch", mock_get_items_to_fetch
    )
    assert fetch_items([], True) == FetchItemsResult(unsuccessful=[], successful=[])


@pytest.mark.parametrize("input_force_update", (True, False))
def test_fetch_items_main(monkeypatch: pytest.MonkeyPatch, input_force_update: bool):
    called_get_items_to_fetch = False
    called_get_items = False
    called_create_item_categories = False
    called_fetch_child_items = False
    called_make_items_from_child_items_if_not_exist = False
    called_create_item = False

    input_item_codes = ["123"]
    items_to_fetch = ["012", "123"]
    parsed_items = [SimpleNamespace(item_code="123")]

    def mock_get_items_to_fetch(item_codes: list[str], force_update: bool):
        assert item_codes == input_item_codes
        assert force_update == input_force_update
        nonlocal called_get_items_to_fetch
        called_get_items_to_fetch = True
        return items_to_fetch

    def mock_get_items(item_codes: list[str]):
        assert item_codes == items_to_fetch
        nonlocal called_get_items
        called_get_items = True
        return parsed_items

    def mock_create_item_categories(items: list[Any]):
        assert items == parsed_items
        nonlocal called_create_item_categories
        called_create_item_categories = True

    def mock_fetch_child_items(items: list[Any], force_update: bool):
        assert items == parsed_items
        assert force_update == input_force_update
        nonlocal called_fetch_child_items
        called_fetch_child_items = True

    def mock_make_items_from_child_items_if_not_exist(item: Any):
        assert item == parsed_items[0]
        nonlocal called_make_items_from_child_items_if_not_exist
        called_make_items_from_child_items_if_not_exist = True

    def mock_called_create_item(item: Any):
        assert item == parsed_items[0]
        nonlocal called_create_item
        called_create_item = True

    monkeypatch.setattr(
        comfort.integrations.ikea, "_get_items_to_fetch", mock_get_items_to_fetch
    )
    monkeypatch.setattr(ikea_api.wrappers, "get_items", mock_get_items)
    monkeypatch.setattr(
        comfort.integrations.ikea,
        "_create_item_categories",
        mock_create_item_categories,
    )
    monkeypatch.setattr(
        comfort.integrations.ikea, "_fetch_child_items", mock_fetch_child_items
    )
    monkeypatch.setattr(
        comfort.integrations.ikea,
        "_make_items_from_child_items_if_not_exist",
        mock_make_items_from_child_items_if_not_exist,
    )
    monkeypatch.setattr(
        comfort.integrations.ikea, "_create_item", mock_called_create_item
    )

    resp = fetch_items(input_item_codes, input_force_update)
    assert resp == FetchItemsResult(unsuccessful=["012"], successful=["123"])

    assert called_get_items_to_fetch
    assert called_get_items
    assert called_create_item_categories
    assert called_fetch_child_items
    assert called_make_items_from_child_items_if_not_exist
    assert called_create_item


def test_get_items_success(monkeypatch: pytest.MonkeyPatch, item_no_children: Item):
    def mock_fetch_items(item_codes: str, force_update: bool):
        assert force_update
        return FetchItemsResult(unsuccessful=[], successful=[item_codes])

    monkeypatch.setattr(comfort.integrations.ikea, "fetch_items", mock_fetch_items)
    item_no_children.db_insert()

    res = get_items(item_codes=item_no_children.item_code)[0]
    assert res.item_code == item_no_children.item_code
    assert res.item_name == item_no_children.item_name
    assert res.rate == item_no_children.rate
    assert res.weight == 0.0


def test_get_items_failure(monkeypatch: pytest.MonkeyPatch):
    mock_item_codes = ["2131418", "147126876"]

    def mock_fetch_items(item_codes: str, force_update: bool):
        assert force_update
        return FetchItemsResult(unsuccessful=mock_item_codes, successful=[])

    monkeypatch.setattr(comfort.integrations.ikea, "fetch_items", mock_fetch_items)

    get_items(item_codes="81042840")
    import frappe

    assert f"Cannot fetch those items: {', '.join(mock_item_codes)}" in str(
        frappe.message_log  # type: ignore
    )
