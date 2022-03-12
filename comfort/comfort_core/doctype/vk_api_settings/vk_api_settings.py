from __future__ import annotations

from comfort.utils import TypedDocument


class VkApiSettings(TypedDocument):
    group_token: str | None

    def on_change(self) -> None:
        self.clear_cache()
