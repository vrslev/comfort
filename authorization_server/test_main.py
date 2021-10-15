import ikea_api
import main
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from main import decode_secret, encode_secret

SECRET_KEY = "BkilT9yfx3WUY9uCf0OWxX8agz36Q4l5NAWzpq7ZRSk="  # nosec


@pytest.fixture(autouse=True)
def secret_key_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", SECRET_KEY)


@pytest.fixture
def client():
    from main import app

    with TestClient(app) as test_client:
        yield test_client


def test_decode_secret():
    secret = "my_secret"  # nosec
    s = Fernet(SECRET_KEY.encode())
    dumped_secret: str = s.encrypt(secret.encode()).decode()  # type: ignore
    assert decode_secret(dumped_secret) == secret


def test_encode_secret():
    secret = "my_secret"  # nosec
    assert decode_secret(encode_secret(secret)) == secret


def test_main(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    exp_username = "my_username"
    exp_password = "my_password"  # nosec
    exp_token = "my_new_token"  # nosec

    class NewIkeaApi(ikea_api.IkeaApi):
        def login(self, username: str, password: str):
            assert username == exp_username
            assert password == exp_password
            self._token = exp_token

    monkeypatch.setattr(main, "IkeaApi", NewIkeaApi)

    response = client.post(
        "/",
        json={
            "username": encode_secret(exp_username),
            "password": encode_secret(exp_password),
        },
    )
    assert response.status_code == 200
    assert decode_secret(response.json()["token"]) == exp_token
