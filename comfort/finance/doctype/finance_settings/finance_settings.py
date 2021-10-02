from comfort import TypedDocument


class FinanceSettings(TypedDocument):
    def on_change(self):
        self.clear_cache()
