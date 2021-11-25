from __future__ import annotations

import re
from typing import Any

from ikea_api._api import API

import frappe


class Kvartiroteka(API):
    _design_id: str
    _rooms: list[dict[str, Any]]
    _images: list[str] = []

    def __init__(self):
        super().__init__("https://kvartiroteka.ikea.ru/data/_/items")
        self._session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json;charset=utf-8",
            }
        )

    def _parse_design_id(self, url: str):
        matches = re.findall(r"#/[^/]+/[^/]+/([^/]+)", url)
        if not matches:
            raise RuntimeError(f"Invalid Kvartiroteka url: {url}")
        self._design_id = matches[0]

    def _get_rooms(self):
        # TODO: Remove this type hint after ikea api update
        resp: Any = self._get(
            endpoint=f"{self.endpoint}/design_room",
            params={"filter[design_id.url][eq]": self._design_id},
        )
        self._rooms = resp["data"]

    def _get_images(self):
        for room in self._rooms:
            # TODO: Remove this type annotation after fix in ikea_api
            resp: Any = self._get(
                endpoint=f"{self.endpoint}/block",
                params={
                    "fields": "views.view_id.image.*",
                    "limit": "-1",
                    "filter[room_id][eq]": room["room_id"],
                    "filter[design_id][eq]": room["design_id"],
                },
            )
            for block in resp["data"]:
                for view in block["views"]:
                    if view and view.get("view_id"):
                        self._images.append(
                            view["view_id"]["image"]["data"]["full_url"]
                        )

    def __call__(self, url: str):  # pragma: no cover
        self._parse_design_id(url)
        self._get_rooms()
        self._get_images()
        return self._images


@frappe.whitelist(allow_guest=True)
def main(url: str):  # pragma: no cover
    return Kvartiroteka()(url)
