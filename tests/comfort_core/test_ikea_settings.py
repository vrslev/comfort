from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from comfort.comfort_core.doctype.ikea_settings.ikea_settings import (
    IkeaSettings,
    get_authorized_api,
    get_guest_api,
)
from frappe.exceptions import ValidationError
from frappe.utils import add_to_date, get_datetime
from tests.conftest import mock_token


def is_same_date(first: Any, second: Any):
    return first.replace(minute=0, second=0, microsecond=0) == second.replace(
        minute=0, second=0, microsecond=0
    )


_testdata = ("token", "expiration"), (
    (None, None),
    ("sometoken", None),
    ("sometoken", datetime.now()),
)


@pytest.mark.parametrize(*_testdata)
def test_get_guest_api_update(
    ikea_settings: IkeaSettings, token: str | None, expiration: datetime | None
):
    ikea_settings.guest_token = token  # type: ignore
    ikea_settings.guest_token_expiration = expiration  # type: ignore
    ikea_settings.save()
    get_guest_api()
    ikea_settings.reload()
    assert ikea_settings.guest_token == mock_token
    assert is_same_date(
        get_datetime(ikea_settings.guest_token_expiration), add_to_date(None, days=30)
    )


def test_get_guest_api_no_update(ikea_settings: IkeaSettings):
    new_token, new_expiration = "fff", add_to_date(None, days=25)
    ikea_settings.guest_token = new_token
    ikea_settings.guest_token_expiration = new_expiration
    ikea_settings.save()
    get_guest_api()
    ikea_settings.reload()
    assert ikea_settings.guest_token == new_token
    assert is_same_date(
        get_datetime(ikea_settings.guest_token_expiration), new_expiration
    )


@pytest.mark.usefixtures("ikea_settings")
def test_get_guest_api_return():
    assert get_guest_api().reveal_token() == mock_token


@pytest.mark.parametrize(*_testdata)
def test_get_authorized_api_update(
    ikea_settings: IkeaSettings, token: str | None, expiration: datetime | None
):
    ikea_settings.authorized_token = token  # type: ignore
    ikea_settings.authorized_token_expiration = expiration  # type: ignore
    ikea_settings.save()
    get_authorized_api()
    ikea_settings.reload()
    assert ikea_settings.authorized_token == mock_token
    assert is_same_date(
        get_datetime(ikea_settings.authorized_token_expiration),
        add_to_date(None, hours=24),
    )


def test_get_authorized_api_no_update(ikea_settings: IkeaSettings):
    new_token, new_expiration = "fff", add_to_date(None, hours=5)
    ikea_settings.authorized_token = new_token
    ikea_settings.authorized_token_expiration = new_expiration
    ikea_settings.save()
    get_authorized_api()
    ikea_settings.reload()
    assert ikea_settings.authorized_token == new_token
    assert is_same_date(
        get_datetime(ikea_settings.authorized_token_expiration), new_expiration
    )


@pytest.mark.usefixtures("ikea_settings")
def test_get_authorized_api_return():
    assert get_authorized_api().reveal_token() == mock_token


def test_get_authorized_api_raises_on_login_data_missing(ikea_settings: IkeaSettings):
    ikea_settings.username = ikea_settings.password = None  # type: ignore
    ikea_settings.save()
    with pytest.raises(
        ValidationError, match="Enter login and password in Ikea Settings"
    ):
        get_authorized_api()


# TODO
# -        or convert_to_datetime(doc.guest_token_expiration) <= now_datetime()
# +        or convert_to_datetime(doc.guest_token_expiration) < now_datetime()
# TODO
#      if (
# -        doc.guest_token is None
# -        or doc.guest_token_expiration is None
# +        doc.guest_token is None and doc.guest_token_expiration is None
# TODO
# -        or convert_to_datetime(doc.authorized_token_expiration) <= now_datetime()
# +        or convert_to_datetime(doc.authorized_token_expiration) < now_datetime()
# TODO
# -        if doc.username is None or password is None:
# +        if doc.username is None and password is None:
