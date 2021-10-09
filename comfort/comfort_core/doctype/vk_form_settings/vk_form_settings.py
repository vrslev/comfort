from frappe.model.document import Document


class VkFormSettings(Document):
    api_secret: str
    group_id: int
