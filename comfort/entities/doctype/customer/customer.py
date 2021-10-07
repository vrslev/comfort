from __future__ import annotations

from typing import Literal, overload
from urllib.parse import parse_qs, urlparse

from comfort import TypedDocument, ValidationError, _

# TODO: Validate phone number


@overload
def parse_vk_id(vk_url: str) -> str:  # pragma: no cover
    ...


@overload
def parse_vk_id(vk_url: None) -> None:  # pragma: no cover
    ...


def parse_vk_id(vk_url: str | None):
    if not vk_url:
        return

    parsed_url = urlparse(vk_url)
    if "vk.com" in parsed_url.netloc and "im" in parsed_url.path:
        query = parse_qs(parsed_url.query)
        if "sel" in query:
            vk_id = query["sel"][0]
            if vk_id and int(vk_id):
                return vk_id

    raise ValidationError(_("Invalid VK URL"))


class Customer(TypedDocument):
    image: str
    gender: Literal["Male", "Female"]
    customer_group: str
    vk_id: str | None
    vk_url: str | None
    phone: str | None
    city: str | None
    address: str | None

    def validate(self):
        self.vk_id = parse_vk_id(self.vk_url)
