from __future__ import annotations

import re
from typing import Iterable, Literal, NamedTuple, overload
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import frappe
from comfort import (
    TypedDocument,
    ValidationError,
    _,
    doc_exists,
    get_all,
    get_doc,
    get_value,
)
from comfort.integrations.vk_api import User, VkApi


class ParseVkUrlResponse(NamedTuple):
    vk_id: str
    vk_url: str


@overload
def parse_vk_url(vk_url: str) -> ParseVkUrlResponse:
    ...


@overload
def parse_vk_url(vk_url: None) -> None:
    ...


def parse_vk_url(vk_url: str | None):
    if not vk_url:
        return

    parsed_url = urlparse(vk_url)
    query = parse_qs(parsed_url.query)
    if "vk.com" in parsed_url.netloc and "im" in parsed_url.path and query.get("sel"):
        vk_id = query["sel"][0]
        components = (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            "",
            urlencode({"sel": vk_id}, doseq=True),
            "",
        )
        new_url = urlunparse(components)
        return ParseVkUrlResponse(vk_id, new_url)

    raise ValidationError(_("Invalid VK URL"))


class Customer(TypedDocument):
    image: str
    gender: Literal["Male", "Female"] | None
    customer_group: str
    vk_id: str | None
    vk_url: str | None
    phone: str | None
    city: str | None
    address: str | None

    def before_insert(self):
        # Find and set unique name (with number suffix if needed)
        regex = re.compile(r" (\d+)$")
        while True:
            if not doc_exists("Customer", self.name):
                break
            if matches := regex.findall(self.name):
                idx = int(matches[0]) + 1
                self.name = f"{regex.sub('', self.name)} {str(idx)}"
            else:
                self.name = f"{self.name} 2"

    def validate(self):
        if self.vk_url:
            self.vk_id, self.vk_url = parse_vk_url(self.vk_url)
        self.update_info_from_vk()

    def _vk_service_token_in_settings(self):
        token: str | None = get_value("Vk Api Settings", fieldname="app_service_token")
        if token:
            return True
        else:
            frappe.msgprint(_("Enter VK App service token in Vk Api Settings"))
            return False

    def update_info_from_vk(self):
        if self.vk_id is None:
            return
        if not self._vk_service_token_in_settings():
            return

        users = _get_vk_users_for_customers((self,))
        _update_customer_from_vk_user(self, users[self.vk_id])


def _get_vk_users_for_customers(customers: Iterable[Customer]) -> dict[str, User]:
    vk_id_to_customer_name_map = {
        c.name: c.vk_id for c in customers if c.vk_id is not None
    }
    user_ids = list(vk_id_to_customer_name_map.values())
    if not user_ids:
        return {}

    users = VkApi().get_users(user_ids)
    active_users = [u for u in users if not u.deactivated]
    return {str(u.id): u for u in active_users}


def _update_customer_from_vk_user(customer: Customer, user: User):
    if not customer.gender:
        customer.gender = {None: None, 0: None, 1: "Female", 2: "Male"}[user.sex]  # type: ignore
    if user.photo_max_orig:
        customer.image = user.photo_max_orig
    if not customer.city and user.city and user.city.title:
        customer.city = user.city.title


def update_all_customers_from_vk():
    customers = get_all(Customer, fields=("name", "vk_id"))
    users = _get_vk_users_for_customers(customers)
    for customer_values in customers:
        if customer_values.vk_id not in users:
            continue
        doc = get_doc(Customer, customer_values.name)
        _update_customer_from_vk_user(doc, users[customer_values.vk_id])  # type: ignore
        doc.save()
