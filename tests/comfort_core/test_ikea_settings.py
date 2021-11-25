from __future__ import annotations

from calendar import timegm
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

import frappe
from comfort.comfort_core.doctype.ikea_settings.ikea_settings import (
    IkeaSettings,
    convert_to_datetime,
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


test_date = datetime(year=2021, month=10, day=13)


@pytest.mark.parametrize(
    ("input", "output"),
    (
        (test_date, test_date),
        ("2021-10-13", test_date),
    ),
)
def test_convert_to_datetime(input: str | datetime, output: datetime):
    assert convert_to_datetime(input) == output


_testdata = ("token", "expiration"), (
    (None, None),
    ("sometoken", None),
    ("sometoken", datetime.now()),
    (None, datetime.now()),
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
    assert get_guest_api().token == mock_token


@pytest.mark.parametrize(*_testdata)
def test_get_authorized_api_update(
    ikea_settings: IkeaSettings,
    token: str | None,
    expiration: datetime | None,
):
    ikea_settings.authorized_token = token
    if expiration:
        ikea_settings.authorized_token_expiration = timegm(
            (expiration - timedelta(days=1)).astimezone(timezone.utc).utctimetuple()
        )
    else:
        ikea_settings.authorized_token_expiration = None

    ikea_settings.save()
    with pytest.raises(ValidationError, match="Update authorization info"):
        get_authorized_api()


def test_get_authorized_api_no_update(ikea_settings: IkeaSettings):
    new_expiration = timegm(
        (datetime.now(tz=timezone.utc) + timedelta(hours=1)).utctimetuple()
    )
    ikea_settings.authorized_token = mock_token
    ikea_settings.authorized_token_expiration = new_expiration
    ikea_settings.save()
    frappe.clear_document_cache("Ikea Settings", "Ikea Settings")
    get_authorized_api()
    ikea_settings.reload()
    assert ikea_settings.authorized_token == mock_token
    assert int(ikea_settings.authorized_token_expiration) == new_expiration


@pytest.mark.usefixtures("ikea_settings")
def test_get_authorized_api_return():
    assert get_authorized_api().token == mock_token
