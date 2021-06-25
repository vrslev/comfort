import re
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _
from frappe.model.document import Document


class Customer(Document):
    def validate(self):
        self.validate_vk_url()
        self.set_vk_id()

    def validate_vk_url(self):
        parsed = urlparse(self.vk_url)
        ok = False
        if 'vk.com' in parsed.netloc and 'im' in parsed.path:
            query = parse_qs(parsed.query)
            if 'sel' in query:
                ok = True

        if not ok:
            frappe.throw(_('Wrong VK URL'))

    def set_vk_id(self):
        if self.vk_url:
            res = re.findall(r'sel=(\d+)', self.vk_url)
            if len(res) > 0:
                self.vk_id = res[0]

        if not self.vk_id:
            frappe.throw(_('Cannot extract VK ID from URL'))

