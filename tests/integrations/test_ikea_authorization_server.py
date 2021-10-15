import json
from typing import Any

import pytest
import requests
import responses
from cryptography.fernet import Fernet

from comfort import get_doc
from comfort.comfort_core.doctype.ikea_authorization_server_settings.ikea_authorization_server_settings import (
    IkeaAuthorizationServerSettings,
)
from comfort.integrations.ikea_authorization_server import (
    _fetch_token,
    _get_endpoint_and_secret_key,
)
from frappe.exceptions import ValidationError


@pytest.fixture
def ikea_authorization_server_settings():
    doc = get_doc(IkeaAuthorizationServerSettings)
    doc.endpoint = "https://example.com"
    doc.secret_key = Fernet.generate_key().decode()
    doc.save()
    return doc


@pytest.mark.parametrize(
    ("set_endpoint", "set_secret_key"), ((True, False), (False, True), (False, False))
)
def test_get_endpoint_and_secret_key_raises(set_endpoint: bool, set_secret_key: bool):
    doc = get_doc(IkeaAuthorizationServerSettings)
    if set_endpoint:
        doc.endpoint = "https://example.com"
    if set_secret_key:
        doc.secret_key = "test key"
    doc.save()
    with pytest.raises(
        ValidationError,
        match="Enter endpoint and secret key in Ikea Authorization Server Settings",
    ):
        _get_endpoint_and_secret_key()


def test_get_endpoint_and_secret_key_passes(
    ikea_authorization_server_settings: IkeaAuthorizationServerSettings,
):
    assert _get_endpoint_and_secret_key() == (
        ikea_authorization_server_settings.endpoint,
        ikea_authorization_server_settings.secret_key,
    )


@responses.activate
def test_fetch_token_raises(
    ikea_authorization_server_settings: IkeaAuthorizationServerSettings,
):
    secret_key = ikea_authorization_server_settings.secret_key
    endpoint = ikea_authorization_server_settings.endpoint
    f = Fernet(secret_key.encode())
    username = "my_username"
    password = "my_password"  # nosec
    exp_err_msg = "my_exp_err_msg"

    def request_callback(
        request: requests.PreparedRequest,
    ) -> tuple[int, dict[Any, Any], str]:
        payload = json.loads(request.body)  # type: ignore
        assert f.decrypt(payload["username"].encode()).decode() == username
        assert f.decrypt(payload["password"].encode()).decode() == password
        return 200, {}, exp_err_msg

    responses.add_callback(responses.POST, endpoint, callback=request_callback)
    with pytest.raises(ValueError, match=exp_err_msg):
        _fetch_token(endpoint, secret_key, username, password)


@responses.activate
def test_fetch_token_passes(
    ikea_authorization_server_settings: IkeaAuthorizationServerSettings,
):
    secret_key = ikea_authorization_server_settings.secret_key
    endpoint = ikea_authorization_server_settings.endpoint
    f = Fernet(secret_key.encode())
    username = "my_username"
    password = "my_password"  # nosec
    exp_token = "my_token"  # nosec

    def request_callback(
        request: requests.PreparedRequest,
    ) -> tuple[int, dict[Any, Any], str]:
        payload = json.loads(request.body)  # type: ignore
        assert f.decrypt(payload["username"].encode()).decode() == username
        assert f.decrypt(payload["password"].encode()).decode() == password
        return 200, {}, json.dumps({"token": f.encrypt(exp_token.encode()).decode()})

    responses.add_callback(responses.POST, endpoint, callback=request_callback)
    assert _fetch_token(endpoint, secret_key, username, password) == exp_token
