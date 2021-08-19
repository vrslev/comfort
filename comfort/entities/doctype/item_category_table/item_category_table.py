from frappe.model.document import Document

from ..item_category.item_category import ItemCategory


class ItemCategoryTable(Document):
    item_category: ItemCategory
