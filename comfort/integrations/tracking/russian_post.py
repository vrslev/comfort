from typing import Any, Literal

import requests
from pydantic import BaseModel


class RussianPostError(Exception):
    response: requests.Response

    def __init__(self, msg: Any, response: requests.Response) -> None:
        self.response = response
        super().__init__(msg)


class TrackingItem(BaseModel):
    barcode: str
    globalStatus: Literal[
        "RETURNED", "ARCHIVED", "ARRIVED", "REGISTERED", "IN PROGRESS"
    ]

    def is_arrived(self):
        return self.globalStatus == "ARRIVED"


class _ResponseItem(BaseModel):
    trackingItem: TrackingItem


class _Response(BaseModel):
    response: list[_ResponseItem]


def track(barcode: str) -> TrackingItem:
    response = requests.post(
        "https://www.pochta.ru/tracking",
        headers={
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.pochta.ru",
            "Accept-Language": "en-GB,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            "Referer": "https://www.pochta.ru/tracking",
            "Accept-Encoding": "gzip, deflate, br",
        },
        params={
            "p_p_id": "trackingPortlet_WAR_portalportlet",
            "p_p_lifecycle": 2,
            "p_p_state": "normal",
            "p_p_mode": "view",
            "p_p_resource_id": "tracking.get-by-barcodes",
            "p_p_cacheability": "cacheLevelPage",
            "p_p_col_id": "column-1",
            "p_p_col_count": 2,
        },
        data=f"barcodes={barcode}",
    )
    data = response.json()
    if "error" in data:
        raise RussianPostError(msg=data["error"], response=response)
    return _Response(**data).response[0].trackingItem
