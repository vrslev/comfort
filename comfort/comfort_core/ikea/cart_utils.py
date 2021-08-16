from __future__ import annotations

from typing import Any

from ikea_api.auth import get_authorized_token, get_guest_token
from ikea_api.endpoints import Cart, OrderCapture, Purchases
from ikea_api.errors import IkeaApiError
from ikea_api_parser import DeliveryOptions, PurchaseHistory, PurchaseInfo

import frappe
from comfort import ValidationError
from comfort.comfort_core.doctype.ikea_cart_settings.ikea_cart_settings import (
    IkeaCartSettings,
)
from frappe.utils.data import add_to_date, get_datetime, now_datetime
from frappe.utils.password import get_decrypted_password


class IkeaCartUtils:
    def __init__(self):
        settings: IkeaCartSettings = frappe.get_single("Ikea Cart Settings")
        self.zip_code: str = settings.zip_code
        self.username: str = settings.username
        self.password: str = get_decrypted_password(
            "Ikea Cart Settings", "Ikea Cart Settings", raise_exception=False
        )
        self.guest_token: str = settings.guest_token
        self.authorized_token: str = settings.authorized_token

    def get_token(self, authorize: bool = False) -> str:
        from datetime import datetime

        doc: IkeaCartSettings = frappe.get_single("Ikea Cart Settings")
        if not authorize:
            guest_token_expiration_time: datetime = get_datetime(
                doc.guest_token_expiration_time
            )
            if not self.guest_token or guest_token_expiration_time <= now_datetime():
                self.guest_token = get_guest_token()
                doc.guest_token = self.guest_token
                doc.guest_token_expiration_time = add_to_date(None, hours=720)
                doc.save()
                frappe.db.commit()
            return self.guest_token
        else:
            authorized_token_expiration_time: datetime = get_datetime(
                doc.authorized_token_expiration_time
            )
            if (
                not self.authorized_token
                or authorized_token_expiration_time <= now_datetime()
            ):
                if not self.username and not self.password:
                    raise ValidationError("Введите логин и пароль в настройках")
                self.authorized_token = get_authorized_token(
                    self.username, self.password
                )
                doc.authorized_token = self.authorized_token
                doc.authorized_token_expiration_time = add_to_date(None, hours=24)
                doc.save()
                frappe.db.commit()
            return self.authorized_token

    def get_delivery_services(self, items: dict[str, int]) -> dict[str, Any]:
        self.get_token()
        adding = self.add_items_to_cart(self.guest_token, items)
        order_capture = OrderCapture(self.guest_token, self.zip_code)
        try:
            response = order_capture.get_delivery_services()
            parsed = DeliveryOptions(response).parse()
            return {"options": parsed, "cannot_add": adding["cannot_add"]}
        except IkeaApiError:  # TODO: Make like in cih
            frappe.msgprint(
                "Нет доступных способов доставки", alert=True, indicator="red"
            )

    def add_items_to_cart(self, token: str, items: dict[str, int]) -> dict[str, Any]:
        cart = Cart(token)
        cart.clear()
        res: dict[str, None | list[Any] | dict[str, Any]] = {
            "cannot_add": [],
            "message": None,
        }
        while True:
            try:
                res["message"] = cart.add_items(items)
                break
            except IkeaApiError as e:  # TODO: was WrongItemCodeError (take from cih)
                [items.pop(i) for i in e.args[0]]
                if not res["cannot_add"]:
                    res["cannot_add"] = []
                res["cannot_add"] += e.args[0]
        return res

    def add_items_to_cart_authorized(self, items: dict[str, int]) -> dict[Any, Any]:
        token = self.get_token(authorize=True)
        self.add_items_to_cart(token, items)
        return Cart(token).show()

    def get_purchase_history(self) -> list[dict[Any, Any]]:
        token = self.get_token(authorize=True)
        purchases = Purchases(token)
        response = purchases.history()
        return PurchaseHistory(response).parse()

    def get_purchase_info(
        self, purchase_id: str | int, use_lite_id: bool = False
    ) -> dict[str, Any]:
        token = self.get_token(authorize=True)
        purchases = Purchases(token)
        email = self.username if use_lite_id else None
        response = purchases.order_info(purchase_id, email=email)
        return PurchaseInfo(response).parse()
