from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

import frappe
from comfort.comfort_core.doctype.telegram_settings.telegram_settings import (
    TelegramSettings,
    get_bot,
    get_chats,
    send_message,
)


class FakeBot(MagicMock):
    def send_message(self, *args: Any, **kwargs: Any):
        pass

    def get_updates(self):
        return [
            frappe._dict(
                {
                    "my_chat_member": frappe._dict(
                        {
                            "old_chat_member": {
                                "status": "left",
                                "user": frappe._dict(
                                    {
                                        "id": 428190844,
                                        "username": "some_random_test_bot_name_bot",
                                        "is_bot": True,
                                        "first_name": "Yet Another Test Bot",
                                    }
                                ),
                                "until_date": None,
                            },
                            "new_chat_member": frappe._dict(
                                {
                                    "can_be_edited": False,
                                    "can_change_info": True,
                                    "is_anonymous": False,
                                    "can_edit_messages": True,
                                    "can_delete_messages": True,
                                    "can_manage_chat": True,
                                    "status": "administrator",
                                    "can_restrict_members": True,
                                    "user": frappe._dict(
                                        {
                                            "id": 428190844,
                                            "username": "some_random_test_bot_name_bot",
                                            "is_bot": True,
                                            "first_name": "Yet Another Test Bot",
                                        }
                                    ),
                                    "can_manage_voice_chats": True,
                                    "can_post_messages": True,
                                    "can_invite_users": True,
                                    "can_promote_members": False,
                                    "until_date": None,
                                }
                            ),
                            "chat": frappe._dict(
                                {
                                    "id": -249104912890,
                                    "title": "Test Channel",
                                    "type": "channel",
                                }
                            ),
                            "date": 1630059515,
                            "from": frappe._dict(
                                {
                                    "language_code": "en",
                                    "id": 248091841,
                                    "username": "some_random_username",
                                    "is_bot": False,
                                    "first_name": "John",
                                }
                            ),
                        }
                    ),
                    "update_id": 839065573,
                }
            )
        ]


@pytest.fixture
def telegram_settings(monkeypatch: MonkeyPatch) -> TelegramSettings:
    monkeypatch.setattr("telegram.Bot", FakeBot)
    doc: TelegramSettings = frappe.get_doc(
        {
            "name": "Telegram Settings",
            "doctype": "Telegram Settings",
            "bot_token": "28910482:82359djtg3fi0denjk",
            "chat_id": -103921437849,
        }
    )
    doc.save()
    return doc


def test_get_bot_raises_when_no_token(telegram_settings: TelegramSettings):
    telegram_settings.db_set("bot_token", None)

    with pytest.raises(frappe.ValidationError, match="Enter Bot Token first"):
        get_bot()


@pytest.mark.usefixtures("telegram_settings")
def test_get_chats():
    assert get_chats() == [{"id": -249104912890, "title": "Test Channel"}]


def test_send_message(monkeypatch: MonkeyPatch, telegram_settings: TelegramSettings):
    class FakeFakeBot(FakeBot):
        def send_message(self, *args: Any, **kwargs: Any):
            assert int(kwargs.get("chat_id")) == telegram_settings.chat_id
            return super().send_message()

    monkeypatch.setattr("telegram.Bot", FakeFakeBot)
    send_message()


def test_send_message_raises_when_no_chat_id(telegram_settings: TelegramSettings):
    telegram_settings.db_set("chat_id", None)
    with pytest.raises(frappe.ValidationError, match="Get Chat ID first"):
        send_message()
