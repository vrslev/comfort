from __future__ import annotations

import asyncio
import re
from typing import Any, Iterable

import ikea_api
from ikea_api.abc import Endpoint, SessionInfo, endpoint
from ikea_api.base_ikea_api import BaseIkeaAPI
from ikea_api.error_handlers import handle_json_decode_error

import frappe
from comfort.integrations.ikea import get_constants


def parse_design_id_from_url(url: str) -> str:
    matches = re.findall(r"#/[^/]+/[^/]+/([^/]+)", url)
    if not matches:
        raise RuntimeError(f"Invalid Kvartiroteka url: {url}")
    return matches[0]


def parse_images_from_blocks(blocks: dict[str, Any]) -> Iterable[str]:
    for block in blocks["data"]:
        for view in block["views"]:
            if view and view.get("view_id"):
                yield view["view_id"]["image"]["data"]["full_url"]


class Kvartiroteka(BaseIkeaAPI):
    def _get_session_info(self) -> SessionInfo:
        return SessionInfo(
            base_url="https://kvartiroteka.ikea.ru/data/_/items",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json;charset=utf-8",
            },
        )

    @endpoint(handlers=[handle_json_decode_error])
    def get_rooms(self, design_id: str) -> Endpoint[list[dict[str, Any]]]:
        response = yield self._RequestInfo(
            "GET", "/design_room", params={"filter[design_id.url][eq]": design_id}
        )
        return response.json["data"]

    @endpoint(handlers=[handle_json_decode_error])
    def get_images(self, room: dict[str, Any]) -> Endpoint[Iterable[str]]:
        params = {
            "fields": "views.view_id.image.*",
            "limit": "-1",
            "filter[room_id][eq]": room["room_id"],
            "filter[design_id][eq]": room["design_id"],
        }
        response = yield self._RequestInfo("GET", "/block", params=params)
        return parse_images_from_blocks(response.json)


async def async_main(url: str):
    design_id = parse_design_id_from_url(url)
    api = Kvartiroteka(constants=get_constants())
    rooms = await ikea_api.run_async(api.get_rooms(design_id))
    tasks = [ikea_api.run_async(api.get_images(room)) for room in rooms]

    images: list[str] = []
    for room_images in await asyncio.gather(*tasks):
        images += room_images
    return images


@frappe.whitelist(allow_guest=True)
def main(url: str):  # pragma: no cover
    return asyncio.run(async_main(url))
