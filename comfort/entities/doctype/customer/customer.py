from __future__ import annotations

import re
from typing import Any, Iterable, Literal, NamedTuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import frappe
from comfort.integrations.vk_api import User, VkApi
from comfort.utils import (
    TypedDocument,
    ValidationError,
    _,
    doc_exists,
    get_all,
    get_doc,
    get_value,
)


class ParseVkUrlResult(NamedTuple):
    vk_id: str
    vk_url: str


def parse_vk_url(vk_url: str) -> ParseVkUrlResult:
    url = urlparse(vk_url)
    query = parse_qs(url.query)

    if not ("vk.com" in url.netloc and "im" in url.path and query.get("sel")):
        raise ValidationError(_("Invalid VK URL"))

    vk_id = query["sel"][0]
    params = urlencode({"sel": vk_id}, doseq=True)
    components = (url.scheme, url.netloc, url.path, "", params, "")
    return ParseVkUrlResult(vk_id, urlunparse(components))


def _vk_token_in_settings():
    there = bool(get_value("Vk Api Settings", fieldname="group_token"))
    if not there:
        frappe.msgprint(_("Enter VK App service token in Vk Api Settings"))
    return there


class Customer(TypedDocument):
    image: str
    gender: Literal["Male", "Female"] | None
    vk_id: str | None
    vk_url: str | None
    phone: str | None
    city: str | None
    address: str | None

    def before_insert(self) -> None:
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
        self.name = self.name.strip()

    def validate(self) -> None:
        if self.vk_url:
            self.vk_id, self.vk_url = parse_vk_url(self.vk_url)
        self.update_info_from_vk()

    def update_info_from_vk(self) -> None:
        if self.vk_id and _vk_token_in_settings():
            users = _get_vk_users_for_customers((self,))
            _update_customer_from_vk_user(self, users[self.vk_id])


def _get_vk_users_for_customers(customers: Iterable[Customer]) -> dict[str, User]:
    if ids := [c.vk_id for c in customers if c.vk_id]:
        users = VkApi().get_users(ids)
        return {str(user.id): user for user in users if not user.deactivated}
    else:
        return {}


def _update_customer_from_vk_user(customer: Customer, user: User) -> None:
    if not customer.gender:
        val_to_str: dict[Any, Any] = {None: None, 0: None, 1: "Female", 2: "Male"}
        customer.gender = val_to_str[user.sex]

    if user.photo_max_orig:
        customer.image = user.photo_max_orig

    if not customer.city and user.city:
        customer.city = user.city.title


def update_all_customers_from_vk() -> None:
    customers = get_all(Customer, field=("name", "vk_id"))
    users = _get_vk_users_for_customers(customers)

    for c in customers:
        if not c.vk_id or c.vk_id not in users:
            continue

        doc = get_doc(Customer, c.name)
        _update_customer_from_vk_user(customer=doc, user=users[c.vk_id])
        doc.save()
