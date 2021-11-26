from __future__ import annotations

from comfort import TypedDocument


class VkApiSettings(TypedDocument):
    group_token: str | None

    def on_change(self):
        self.clear_cache()
