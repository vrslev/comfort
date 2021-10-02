from typing import Any

import pytest
from pytest import MonkeyPatch

import frappe
from comfort.comfort_core.doctype.telegram_settings.telegram_settings import (
    TelegramSettings,
    get_bot,
    get_chats,
    send_message,
)
from tests.conftest import FakeBot


def test_get_bot_raises_when_no_token(telegram_settings: TelegramSettings):
    telegram_settings.db_set("bot_token", None)

    with pytest.raises(frappe.ValidationError, match="Enter Bot Token first"):
        get_bot()


@pytest.mark.usefixtures("telegram_settings")
def test_get_chats():
    assert get_chats() == [{"id": "-249104912890", "title": "Test Channel"}]


def test_send_message(monkeypatch: MonkeyPatch, telegram_settings: TelegramSettings):
    class FakeFakeBot(FakeBot):
        def send_message(self, *args: Any, **kwargs: Any):
            assert str(kwargs.get("chat_id", 0)) == telegram_settings.chat_id
            return super().send_message()

    monkeypatch.setattr("telegram.Bot", FakeFakeBot)
    send_message()


def test_send_message_raises_when_no_chat_id(telegram_settings: TelegramSettings):
    telegram_settings.db_set("chat_id", None)
    with pytest.raises(frappe.ValidationError, match="Get Chat ID first"):
        send_message()
