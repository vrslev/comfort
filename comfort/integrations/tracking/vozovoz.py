from typing import Any

import requests
from pydantic import BaseModel, Field


class VozovozError(Exception):
    response: requests.Response

    def __init__(self, msg: Any, response: requests.Response) -> None:
        self.response = response
        super().__init__(msg)


class Status(BaseModel):
    isTaken: bool
    isGiven: bool
    hasArrived: bool
    isCanceled: bool


class Response(BaseModel):
    barcode: str = Field(alias="number")
    status: Status

    def is_arrived(self):
        return self.status.hasArrived


def track(barcode: str) -> Response:
    response = requests.post(
        "https://api.vozovoz.ru/v1/order/mini",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Origin": "https://spb.vozovoz.ru",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            "Referer": "https://spb.vozovoz.ru/",
        },
        json={"orderID": barcode},
    )
    data = response.json()
    if "error" in data:
        raise VozovozError(msg=data["error"], response=response)
    return Response(**data)
