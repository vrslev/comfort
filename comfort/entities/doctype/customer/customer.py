from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from comfort import ValidationError
from frappe import _
from frappe.model.document import Document

# TODO: Validate phone number


class Customer(Document):
    vk_url: str
    vk_id: int | None

    def validate(self):  # pragma: no cover
        self.validate_vk_url_and_set_vk_id()

    def validate_vk_url_and_set_vk_id(self):
        if not self.vk_url:
            self.vk_id = None
            return

        ok = False

        parsed = urlparse(self.vk_url)
        if "vk.com" in parsed.netloc and "im" in parsed.path:
            query = parse_qs(parsed.query)
            if "sel" in query:
                vk_id = query["sel"][0]
                if vk_id and int(vk_id):
                    ok = True
                    self.vk_id = vk_id

        if not ok:
            raise ValidationError(_("Wrong VK URL"))
