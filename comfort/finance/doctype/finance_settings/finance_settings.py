from comfort.utils import TypedDocument


class FinanceSettings(TypedDocument):
    def on_change(self) -> None:
        self.clear_cache()
