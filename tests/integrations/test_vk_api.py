from __future__ import annotations

from typing import Any

import pytest
import requests
import responses

from comfort.comfort_core.doctype.vk_api_settings.vk_api_settings import VkApiSettings
from comfort.integrations.vk_api import User, VkApi, VkApiError
from frappe.exceptions import ValidationError


@pytest.mark.usefixtures("vk_api_settings")
def test_vk_api_init():
    vk = VkApi()
    assert vk.service_token
    assert type(vk._session) == requests.Session


def test_vk_api_get_service_token_from_settings_with_token(
    vk_api_settings: VkApiSettings,
):
    vk = VkApi.__new__(VkApi)
    vk._get_service_token_from_settings()
    assert vk.service_token == vk_api_settings.app_service_token


def test_vk_api_get_service_token_from_settings_no_token():
    vk = VkApi.__new__(VkApi)
    with pytest.raises(
        ValidationError, match="Enter VK App service token in Vk Api Settings"
    ):
        vk._get_service_token_from_settings()


@pytest.fixture
def vk_api(vk_api_settings: VkApiSettings):
    return VkApi()


def test_vk_api_get_params_no_params(vk_api: VkApi):
    vk_api._get_params({})


def test_vk_api_get_params_with_params_plain(vk_api: VkApi):
    assert vk_api._get_params({"key": "value"}) == {
        "access_token": vk_api.service_token,
        "v": vk_api.api_version,
        "lang": vk_api.lang,
        "key": "value",
    }


def test_vk_api_get_params_with_params_with_list(vk_api: VkApi):
    assert vk_api._get_params({"key": "value", "key2": ["value1", 2]}) == {
        "access_token": vk_api.service_token,
        "v": vk_api.api_version,
        "lang": vk_api.lang,
        "key": "value",
        "key2": "value1,2",
    }


def add_mock_response(
    vk_api: VkApi,
    method: str,
    params: dict[str, Any],
    response: Any,
    status: int = 200,
):
    responses.add(
        responses.GET,
        f"https://api.vk.com/method/{method}",
        match=[responses.matchers.query_param_matcher(vk_api._get_params(params))],
        json=response,
        status=status,
    )


vk_api_mock_method = "test.endpoint"
vk_api_mock_params = {"key": "value"}


@responses.activate
def test_vk_api_call_api_success(vk_api: VkApi):
    exp_resp = {"response": "test"}
    add_mock_response(vk_api, vk_api_mock_method, vk_api_mock_params, exp_resp)
    assert (
        vk_api._call_api(vk_api_mock_method, **vk_api_mock_params)
        == exp_resp["response"]
    )


@responses.activate
@pytest.mark.parametrize(
    "exp_resp",
    (
        {"response": "test", "error": {"error_code": 1, "error_msg": "some msg"}},
        {"error": {"error_code": 1, "error_msg": "some msg"}},
    ),
)
def test_vk_api_call_api_failure(vk_api: VkApi, exp_resp: dict[str, Any]):
    add_mock_response(vk_api, vk_api_mock_method, vk_api_mock_params, exp_resp)
    with pytest.raises(VkApiError) as exc_info:
        vk_api._call_api(vk_api_mock_method, **vk_api_mock_params)
    assert exc_info.value.args == (
        exp_resp["error"]["error_code"],
        exp_resp["error"]["error_msg"],
    )


@responses.activate
def test_vk_api_call_api_http_status(vk_api: VkApi):
    add_mock_response(
        vk_api, vk_api_mock_method, vk_api_mock_params, {"response": "test"}, status=500
    )
    with pytest.raises(requests.exceptions.HTTPError):
        vk_api._call_api(vk_api_mock_method, **vk_api_mock_params)


mock_users_get_resp = {
    "response": [
        {
            "first_name": "Иван",
            "id": 1,
            "last_name": "Иванов",
            "can_access_closed": True,
            "is_closed": False,
            "sex": 2,
            "city": {"id": 11, "title": "Москва"},
            "photo_max_orig": "https://sun9-84.userapi.com/s/v1/if1/dsjkfljdet20efIJFWALKjfdew9tru2309ruoij.jpg?size=400x400&quality=96&crop=142,0,1365,1365&ava=1",
        },
        {
            "first_name": "Елена",
            "id": 2,
            "last_name": "Иванова",
            "can_access_closed": False,
            "is_closed": True,
            "sex": 1,
            "city": {"id": 11, "title": "Москва"},
            "photo_max_orig": "https://sun9-42.userapi.com/s/v1/ig2/jdgklwejSAKJFklerwjge39ur9032u`.jpg?size=400x400&quality=96&crop=351,299,945,945&ava=1",
        },
    ]
}


@responses.activate
def test_vk_api_get_users(vk_api: VkApi):
    user_ids = ["1"]
    params = {"user_ids": user_ids, "fields": ["photo_max_orig", "sex", "city"]}
    add_mock_response(vk_api, "users.get", params, mock_users_get_resp)
    assert vk_api.get_users(user_ids) == [
        User(**u) for u in mock_users_get_resp["response"]
    ]
