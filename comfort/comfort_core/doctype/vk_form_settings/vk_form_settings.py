from comfort import TypedDocument


class VkFormSettings(TypedDocument):
    api_secret: str
    group_id: int

    def on_change(self):
        self.clear_cache()
