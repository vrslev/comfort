from comfort.utils import TypedDocument


class VkFormSettings(TypedDocument):
    api_secret: str
    group_id: int

    def on_change(self) -> None:
        self.clear_cache()
