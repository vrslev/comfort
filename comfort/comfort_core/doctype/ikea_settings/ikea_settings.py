from datetime import datetime

import ikea_api
import ikea_api.auth

import frappe
from comfort import ValidationError
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, now_datetime
from frappe.utils.password import get_decrypted_password


class IkeaSettings(Document):
    username: str
    password: str
    zip_code: str
    authorized_token: str
    authorized_token_expiration_time: datetime
    guest_token: str
    guest_token_expiration_time: datetime

    def on_change(self):
        self.clear_cache()


def get_guest_api():
    docname = "Ikea Settings"
    doc: IkeaSettings = frappe.get_cached_doc(docname, docname)

    if not doc.guest_token or doc.guest_token_expiration_time <= now_datetime():
        doc.guest_token = ikea_api.auth.get_guest_token()
        doc.guest_token_expiration_time = add_to_date(None, days=30)
        doc.save()

    return ikea_api.IkeaApi(doc.guest_token)


def get_authorized_api():
    docname = "Ikea Settings"
    doc: IkeaSettings = frappe.get_cached_doc(docname, docname)
    password: str = get_decrypted_password(docname, docname, raise_exception=False)

    if (
        not doc.authorized_token
        or doc.authorized_token_expiration_time <= now_datetime()
    ):
        if not doc.username or not password:
            raise ValidationError(_("Enter login and password in Ikea Settings"))
        doc.authorized_token = ikea_api.auth.get_authorized_token(
            doc.username, password
        )
        doc.authorized_token_expiration_time = add_to_date(None, hours=24)
        doc.save()

    return ikea_api.IkeaApi(doc.authorized_token)
