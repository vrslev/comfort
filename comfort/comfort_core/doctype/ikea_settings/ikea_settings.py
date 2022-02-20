from __future__ import annotations

from datetime import datetime

from comfort import TypedDocument


class IkeaSettings(TypedDocument):
    zip_code: str | None
    authorized_token: str | None
    authorized_token_expiration: int | None
    guest_token: str | None
    guest_token_expiration: datetime | str | None

    def on_change(self):
        self.clear_cache()
