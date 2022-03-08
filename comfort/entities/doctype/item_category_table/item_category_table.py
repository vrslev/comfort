from comfort.utils import TypedDocument

from ..item_category.item_category import ItemCategory


class ItemCategoryTable(TypedDocument):
    item_category: ItemCategory
