from json import JSONDecodeError

import requests
from cryptography.fernet import Fernet
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from comfort import ValidationError, _, get_doc
from comfort.comfort_core.doctype.ikea_authorization_server_settings.ikea_authorization_server_settings import (
    IkeaAuthorizationServerSettings,
)


def _get_endpoint_and_secret_key():
    doc = get_doc(IkeaAuthorizationServerSettings)
    if not doc.endpoint or not doc.secret_key:
        raise ValidationError(
            _("Enter endpoint and secret key in Ikea Authorization Server Settings")
        )
    return doc.endpoint, doc.secret_key


def _get_session():
    session = requests.Session()
    retry = Retry(total=2, status_forcelist=[500])
    adapter = HTTPAdapter(max_retries=retry)  # type: ignore
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _fetch_token(endpoint: str, secret_key: str, username: str, password: str):
    f = Fernet(secret_key.encode())
    payload = {
        "username": f.encrypt(username.encode()).decode(),
        "password": f.encrypt(password.encode()).decode(),
    }
    session = _get_session()
    response = session.post(endpoint, json=payload)

    try:
        rjson = response.json()
    except JSONDecodeError:
        raise ValueError(response.text)

    encoded_token: str = rjson["token"]
    token = f.decrypt(encoded_token.encode()).decode()
    return token


def main(username: str, password: str):  # pragma: no cover
    endpoint, secret_key = _get_endpoint_and_secret_key()
    return _fetch_token(endpoint, secret_key, username, password)
