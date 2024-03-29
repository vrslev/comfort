from __future__ import annotations

import asyncio
import json
import os.path
import re
import sys
from argparse import ArgumentParser
from base64 import b64encode
from configparser import ConfigParser
from dataclasses import dataclass
from html import unescape
from importlib.metadata import distribution
from subprocess import check_call  # nosec
from typing import Any

import ikea_api
import requests
import sentry_sdk
import sentry_sdk.utils
from bs4 import BeautifulSoup
from ikea_api.utils import (
    unshorten_urls_from_ingka_pagelinks as orig_unshorten_urls_from_ingka_pagelinks,
)

PACKAGE_NAME = "comfort_browser_ext"


@dataclass
class Config:
    url: str
    api_key: str
    api_secret: str
    sentry_dsn: str | None


def get_config(directory: str):
    path = os.path.join(directory, "config.ini")
    config = ConfigParser()
    config.read(path)
    no_section = not config.has_section(PACKAGE_NAME)
    if no_section:
        config.add_section(PACKAGE_NAME)
    no_values = not any(config[PACKAGE_NAME].values())
    if no_values:
        for attr in Config.__annotations__.keys():
            config.set(PACKAGE_NAME, attr, "")
    if no_section or no_values:
        with open(path, "a+") as f:
            f.seek(0)
            f.truncate()
            config.write(f)
    if not all(
        (
            config[PACKAGE_NAME]["url"],
            config[PACKAGE_NAME]["api_key"],
            config[PACKAGE_NAME]["api_secret"],
        )
    ):
        raise RuntimeError("Config is incomplete")
    return Config(**config[PACKAGE_NAME])


def init_sentry(config: Config):
    if not config.sentry_dsn:
        return

    release = distribution(PACKAGE_NAME).metadata["Version"]
    sentry_sdk.utils.MAX_STRING_LENGTH = 8192  # Capture full tracebacks from server
    sentry_sdk.init(
        dsn=config.sentry_dsn,
        release=f"{PACKAGE_NAME}@{release}",
        traces_sample_rate=1.0,
        with_locals=True,
    )


def _unshorten_item_urls(soup: BeautifulSoup):
    for btn_tag in soup.find_all(re.compile("a|img|button")):
        btn_tag: BeautifulSoup
        url: str | None = btn_tag.get("data-link-url")  # type: ignore
        if url is not None:
            btn_tag.replace_with(url)

    for a_tag in soup.find_all("a"):
        a_tag: BeautifulSoup
        url: str | None = a_tag.get("title")  # type: ignore
        if url:
            a_tag.replace_with(url)

    return soup


def _unshorten_urls_from_ingka_pagelinks(item_codes: str | list[str]) -> list[str]:
    coro = orig_unshorten_urls_from_ingka_pagelinks(str(item_codes))
    return asyncio.run(coro)


def parse_item_codes(item_codes: str | list[str]) -> list[str]:
    if isinstance(item_codes, str):
        res = [item_codes]
    else:
        res = item_codes
    unshortened = _unshorten_urls_from_ingka_pagelinks(res[0]) if res else []
    res.extend(unshortened)
    return ikea_api.parse_item_codes(res)


def _get_item_codes(html: str):
    soup = BeautifulSoup(unescape(unescape(html)), "html.parser")
    text = _unshorten_item_urls(soup).get_text()
    return parse_item_codes(text)


class FrappeException(Exception):
    def __init__(self, *args: object):
        if len(args) == 1 and isinstance(args[0], str):
            try:  # Try to parse traceback from server
                args = json.loads(args[0])[0]
            except json.decoder.JSONDecodeError:
                pass
        super().__init__(args)


class FrappeApi:
    def __init__(self, url: str, api_key: str, api_secret: str):
        self.url = url
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/json"
        self._authenticate(api_key, api_secret)

    def _authenticate(self, api_key: str, api_secret: str):
        token = b64encode(f"{api_key}:{api_secret}".encode()).decode()
        self._session.headers["Authorization"] = f"Basic {token}"

    def _dump_payload(self, payload: dict[str, Any]):
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                payload[key] = json.dumps(value)
        return payload

    def _handle_response(self, response: requests.Response):
        try:
            rjson: dict[str, Any] = response.json()
        except ValueError:
            raise ValueError(response.text)

        if exc := rjson.get("exc"):
            raise FrappeException(exc)
        if "message" in rjson:
            return rjson["message"]
        elif "data" in rjson:
            return rjson["data"]
        else:
            raise NotImplementedError

    def post(self, **payload: Any):
        response = self._session.post(self.url, json=self._dump_payload(payload))
        return self._handle_response(response)


def _send_sales_order_to_server(
    config: Config, customer_name: str, vk_url: str, item_codes: list[str]
) -> str:
    return FrappeApi(
        url=config.url,
        api_key=config.api_key,
        api_secret=config.api_secret,
    ).post(
        cmd="comfort.integrations.browser_ext.process_sales_order",
        customer_name=customer_name,
        vk_url=vk_url,
        item_codes=item_codes,
    )


def process_sales_order(
    config: Config, html: str, customer_name: str, vk_url: str
):  # pragma: no cover
    item_codes = _get_item_codes(html)
    url = _send_sales_order_to_server(config, customer_name, vk_url, item_codes)
    return check_call(["open", url])


def update_token(config: Config, token: str):
    FrappeApi(
        url=config.url, api_key=config.api_key, api_secret=config.api_secret
    ).post(
        cmd="comfort.integrations.browser_ext.update_token",
        token=token,
    )
    return 0


def parse_args(args: list[str]):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    process_sales_order_parser = subparsers.add_parser("process_sales_order")
    process_sales_order_parser.add_argument("customer_name", type=str)
    process_sales_order_parser.add_argument("vk_url", type=str)
    process_sales_order_parser.add_argument("html", type=str)

    get_token_parser = subparsers.add_parser("update_token")
    get_token_parser.add_argument("token", type=str)

    return parser.parse_args(args)


def main() -> int:
    config = get_config(os.path.dirname(__file__))
    init_sentry(config)
    args = parse_args(sys.argv[1:])

    if args.command == "process_sales_order":
        return process_sales_order(config, args.html, args.customer_name, args.vk_url)
    elif args.command == "update_token":
        return update_token(config, args.token)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
