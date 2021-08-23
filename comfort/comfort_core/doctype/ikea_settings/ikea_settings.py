from datetime import datetime

import ikea_api
import ikea_api.auth

import frappe
from comfort import ValidationError
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, now_datetime


class IkeaSettings(Document):
    username: str
    password: str
    zip_code: str
    authorized_token: str
    authorized_token_expiration: datetime
    guest_token: str
    guest_token_expiration: datetime

    def on_change(self):
        self.clear_cache()


def convert_to_datetime(datetime_str: str) -> datetime:  # pragma: no cover
    return get_datetime(datetime_str)


def get_guest_api():
    doc: IkeaSettings = frappe.get_cached_doc("Ikea Settings", "Ikea Settings")
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
    doc: IkeaSettings = frappe.get_cached_doc("Ikea Settings", "Ikea Settings")
    password: str = doc.get_password(raise_exception=False)
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
