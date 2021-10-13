from __future__ import annotations

from typing import Any, Literal, Optional

import requests
from pydantic import BaseModel, HttpUrl

from comfort import ValidationError, _, get_value


class VkApi:
    service_token: str
    api_version: str = "5.131"
    lang: str = "ru"

    def __init__(self):
        self._get_service_token_from_settings()
        self._session = requests.Session()

    def _get_service_token_from_settings(self):
        token: str | None = get_value("Vk Api Settings", fieldname="app_service_token")
        if token is None:
            raise ValidationError(_("Enter VK App service token in Vk Api Settings"))
        self.service_token = token

    def _get_params(self, params: dict[str, Any]):
        for key in params:
            if isinstance(params[key], list):
                params[key] = ",".join(str(p) for p in params[key])
        params |= {
            "access_token": self.service_token,
            "v": self.api_version,
            "lang": self.lang,
        }
        return params

    def _call_api(self, method: str, **params: Any) -> Any:
        response = self._session.get(
            f"https://api.vk.com/method/{method}", params=self._get_params(params)
        )
        response.raise_for_status()
        data = VkApiResponse(**response.json())
        if data.error:
            raise VkApiError(data.error.error_code, data.error.error_msg)
        return data.response

    def get_users(self, user_ids: list[str]):
        response = self._call_api(
            "users.get",
            user_ids=user_ids,
            fields=["photo_max_orig", "sex", "city"],
        )
        return [User(**u) for u in response]


class VkApiError(Exception):
    pass


class VkApiResponseErrorInfo(BaseModel):
    error_code: int
    error_msg: str


class VkApiResponse(BaseModel):
    response: Optional[Any]
    error: Optional[VkApiResponseErrorInfo]


class UserCity(BaseModel):
    id: int
    title: str


class User(BaseModel):
    id: int
    first_name: str
    last_name: str
    deactivated: Optional[Literal["deleted", "banned"]]
    is_closed: bool
    can_access_closed: bool
    city: Optional[UserCity]
    photo_max_orig: Optional[HttpUrl]
    sex: Optional[Literal[0, 1, 2]]
