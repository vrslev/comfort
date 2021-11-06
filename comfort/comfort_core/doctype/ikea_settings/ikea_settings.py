from __future__ import annotations

from calendar import timegm
from datetime import datetime, timezone

import ikea_api
import ikea_api.auth
from jwt import PyJWT
from jwt.exceptions import ExpiredSignatureError

from comfort import TypedDocument, ValidationError, _, get_cached_doc
from frappe.utils import add_to_date, get_datetime, now_datetime


class IkeaSettings(TypedDocument):
    zip_code: str | None
    authorized_token: str | None
    authorized_token_expiration: int | None
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


def _authorized_token_expired(exp: int):
    now = timegm(datetime.now(tz=timezone.utc).utctimetuple())
    try:
        PyJWT()._validate_exp({"exp": exp}, now, 0)
    except ExpiredSignatureError:
        return True


def get_authorized_api():
    doc = get_cached_doc(IkeaSettings)
    if (
        doc.authorized_token is None
        or doc.authorized_token_expiration is None
        or _authorized_token_expired(doc.authorized_token_expiration)
    ):
        raise ValidationError(_("Update authorization info"))

    return ikea_api.IkeaApi(doc.authorized_token)
