from __future__ import annotations

from typing import Any

import telegram

import frappe
from comfort import ValidationError
from frappe import _
from frappe.model.document import Document


class TelegramSettings(Document):
    bot_token: str | None
    chat_id: str | None


def get_bot():
    token: str | None = frappe.get_value("Telegram Settings", None, "bot_token")
    if token is None:
        raise ValidationError(_("Enter Bot Token first"))
    return telegram.Bot(token)


@frappe.whitelist()
def get_chats():
    bot = get_bot()
    chats: list[dict[str, str | int]] = []
    for update in bot.get_updates():
        if update.my_chat_member:
            c = update.my_chat_member.chat
            chats.append({"id": c.id, "title": c.title})
    return chats


def send_message(*args: Any, **kwargs: Any):
    bot = get_bot()
    chat_id: str | None = frappe.get_value("Telegram Settings", None, "chat_id")
    if chat_id is None:
        raise ValidationError(_("Get Chat ID first"))
    return bot.send_message(*args, chat_id=chat_id, **kwargs)
