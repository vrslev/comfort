from __future__ import annotations

from datetime import datetime

import ikea_api
import ikea_api.auth

from comfort import TypedDocument, ValidationError, _, get_cached_doc
from frappe.utils import add_to_date, get_datetime, now_datetime


class IkeaSettings(TypedDocument):
    username: str | None
    password: str | None
    zip_code: str | None
    authorized_token: str | None
    authorized_token_expiration: datetime | str | None
    guest_token: str | None
    guest_token_expiration: datetime | str | None

    def on_change(self):
        self.clear_cache()


def convert_to_datetime(datetime_str: datetime | str) -> datetime:
    return get_datetime(datetime_str)  # type: ignore


def get_guest_api():
    doc = get_cached_doc(IkeaSettings)
    if (
        doc.guest_token is None
        or doc.guest_token_expiration is None
        or convert_to_datetime(doc.guest_token_expiration) <= now_datetime()
    ):
        doc.guest_token = ikea_api.auth.get_guest_token()
        doc.guest_token_expiration = add_to_date(None, days=30)
        doc.save()

    return ikea_api.IkeaApi(doc.guest_token)


def get_authorized_api():
    doc = get_cached_doc(IkeaSettings)
    password = doc.get_password(raise_exception=False)
    if (
        doc.authorized_token is None
        or doc.authorized_token_expiration is None
        or convert_to_datetime(doc.authorized_token_expiration) <= now_datetime()
    ):
        if doc.username is None or password is None:
            raise ValidationError(_("Enter login and password in Ikea Settings"))
        doc.authorized_token = ikea_api.auth.get_authorized_token(
            doc.username, password
        )
        doc.authorized_token_expiration = add_to_date(None, hours=24)
        doc.save()

    return ikea_api.IkeaApi(doc.authorized_token)
