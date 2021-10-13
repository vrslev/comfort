from __future__ import annotations

from typing import Iterable, Literal, overload
from urllib.parse import parse_qs, urlparse

from comfort import TypedDocument, ValidationError, _, get_all, get_doc
from comfort.integrations.vk_api import User, VkApi

# TODO: Validate phone number
# TODO: Fix vk_url: https://vk.com/im?peers=1111111&sel=111111 (keep only "sel" part)


@overload
def parse_vk_id(vk_url: str) -> str:
    ...


@overload
def parse_vk_id(vk_url: None) -> None:
    ...


def parse_vk_id(vk_url: str | None):
    if not vk_url:
        return

    parsed_url = urlparse(vk_url)
    if "vk.com" in parsed_url.netloc and "im" in parsed_url.path:
        query = parse_qs(parsed_url.query)
        if "sel" in query:
            return query["sel"][0]

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

    def validate(self):
        self.vk_id = parse_vk_id(self.vk_url)
        self.update_info_from_vk()

    def update_info_from_vk(self):  # TODO: Cover
        if self.vk_id is None:
            return
        users = _get_vk_users_for_customers((self,))
        _update_customer_from_vk_user(self, users[self.vk_id])


def _get_vk_users_for_customers(customers: Iterable[Customer]):
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
    customer.gender = {None: None, 0: None, 1: "Female", 2: "Male"}[user.sex]  # type: ignore
    if user.photo_max_orig:
        customer.image = user.photo_max_orig
    if user.city and user.city.title:
        customer.city = user.city.title


def update_all_customers_from_vk():
    customers = get_all(Customer, fields=("name", "vk_id"))
    users = _get_vk_users_for_customers(customers)
    for customer_values in customers:
        if customer_values.vk_id is None or customer_values.vk_id not in users:
            continue
        doc = get_doc(Customer, customer_values.name)
        _update_customer_from_vk_user(doc, users[customer_values.vk_id])
        doc.save()
