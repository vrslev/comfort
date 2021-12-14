import json
import os.path
from typing import Any, Literal, Optional

from pydantic import BaseModel

import frappe
from frappe.frappeclient import FrappeClient
from frappe.translate import get_messages as frappe_get_messages
from frappe.translate import get_translation_dict_from_file, get_translator_url


class Response(BaseModel):
    id: str
    source_text: str
    context: Optional[str]
    translated_text: Optional[str]
    translated: Literal[0, 1]
    translated_by_google: Literal[0, 1]
    contributor_name: Optional[str]
    contributor_email: Optional[str]
    modified_by: Any
    creation: Any


def get_message(text: str):
    if messages := frappe_get_messages("ru", page_length=1, search_text=text):
        return Response(**messages[0])  # type: ignore


frappe.init("site", "../../sites")
frappe.connect()


def add_to_tosendjson(source_id: str, source_text: str, translated_text: str):
    if not os.path.exists("to_send.json"):
        with open("to_send.json", "w") as f:
            json.dump({}, f)
    with open("to_send.json", "r+") as f:
        content: dict[str, dict[str, Any]] = json.load(f)
        content[source_id] = {
            "source_text": source_text,
            "translated_text": translated_text,
            "context": None,
        }
        f.seek(0)
        json.dump(content, f)


def remove_from_toprocessjson(source_text: str):
    with open("to_process.json", "r+") as f:
        content: dict[str, str] = json.load(f)
        if source_text in content:
            del content[source_text]
        f.seek(0)
        f.truncate(0)
        json.dump(content, f)


def get_next_item():
    if not os.path.exists("to_process.json"):
        with open("to_process.json", "w") as f:
            json.dump(get_translation_dict_from_file("test.csv", "ru", "comfort"), f)
    with open("to_process.json", "r+") as f:
        content: dict[str, str] = json.load(f)
        items = list(content.items())
        if items:
            return items[0]
        return None, None


def collect():
    while True:
        before, after = get_next_item()
        if not before or not after:
            break
        response = get_message(before)
        if not response:
            print(f"Not found. original: {before}, translated: {after}")
        elif response.source_text == before and response.translated_text != after:
            add_to_tosendjson(
                source_id=response.id,
                source_text=response.source_text,
                translated_text=after,
            )
            print(
                f"Updated. original: {before}, official: {response.translated_text}, mine: {after}"
            )
        else:
            print(f"Skipped. original: {before}, translated: {after}")
        remove_from_toprocessjson(before)


class PayloadItem(BaseModel):
    source_text: str
    translated_text: str
    context: None
    name: None = None


def split_to_chunks(list_: list[Any], chunk_size: int):
    return (list_[i : i + chunk_size] for i in range(0, len(list_), chunk_size))


def remove_from_tosendjson(id_: str):
    with open("to_send.json", "r+") as f:
        content: dict[str, str] = json.load(f)
        if id_ in content:
            del content[id_]
        f.seek(0)
        f.truncate(0)
        json.dump(content, f)


def send():
    with open("to_send.json") as f:
        items: dict[str, dict[str, Any]] = json.load(f)
        for item in items.copy():
            items[item] = PayloadItem(**items[item]).dict()

    url: str = get_translator_url()
    client = FrappeClient(url)

    for chunk in split_to_chunks(list(items.items()), 5):
        client.post_api(
            "translator.api.add_translations",
            params={
                "language": "ru",
                "contributor_email": "mail@vrslev.com",
                "contributor_name": "Lev",
                "translation_map": json.dumps(dict(chunk)),
            },
        )
        print("Sent chunk")
        for id_, _ in chunk:
            remove_from_tosendjson(id_)


collect()
send()
