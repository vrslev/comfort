from datetime import datetime

from frappe.model.document import Document


class IkeaCartSettings(Document):
    username: str
    password: str
    zip_code: str
    authorized_token: str
    authorized_token_expiration_time: datetime
    guest_token: str
    guest_token_expiration_time: datetime
