import os

import ikea_api.auth
import pyppeteer
import sentry_sdk
from cryptography.fernet import Fernet
from fastapi import Body, FastAPI
from ikea_api import IkeaApi

app = FastAPI()

if sentry_dsn := os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(sentry_dsn, with_locals=False)


def decode_secret(secret: str):
    s = Fernet(os.environ["SECRET_KEY"].encode())
    return s.decrypt(secret.encode()).decode()


def encode_secret(secret: str):
    s = Fernet(os.environ["SECRET_KEY"].encode())
    return s.encrypt(secret.encode()).decode()


def patch_get_driver():
    if not os.environ.get("IN_DOCKER"):
        return

    async def _get_driver():
        return await pyppeteer.launch(
            executablePath="google-chrome-unstable",
            handleSIGINT=False,
            handleSIGTERM=False,
            handleSIGHUP=False,
            args=[
                "--no-sandbox",
                "--window-position=0,0",
                '--user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                + "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 "
                + 'Safari/537.36"',
            ],
        )

    ikea_api.auth._get_driver = _get_driver


def get_token(username: str, password: str) -> str:
    patch_get_driver()
    ikea = IkeaApi()
    ikea.login(username, password)
    return ikea.reveal_token()  # type: ignore


@app.post("/")
def root(username: str = Body(...), password: str = Body(...)):  # type: ignore
    username = decode_secret(username)
    password = decode_secret(password)
    token = get_token(username, password)
    return {"token": encode_secret(token)}
