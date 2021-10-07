from __future__ import annotations

import json
import os.path
import re
import sys
from argparse import ArgumentParser, Namespace
from configparser import ConfigParser
from dataclasses import dataclass
from importlib.metadata import distribution
from subprocess import check_call  # nosec
from typing import Any

import frappeclient.frappeclient
import ikea_api_wrapped
import sentry_sdk
import sentry_sdk.utils
from bs4 import BeautifulSoup
from frappeclient import FrappeClient
from requests import Response

PACKAGE_NAME = "comfort_browser_ext"


def unshorten_item_urls(html: str):
    soup = BeautifulSoup(html, "html.parser")

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


def get_item_codes(html: str):
    text = unshorten_item_urls(html).get_text()
    return ikea_api_wrapped.parse_item_codes(text)


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


class CustomFrappeClient(FrappeClient):  # pragma: no cover
    url: str

    def preprocess(self, params: dict[str, Any]) -> dict[str, Any]:
        return super().preprocess(params)  # type: ignore

    def post_process(self, response: Response) -> Any:
        return super().post_process(response)  # type: ignore

    def post_json(self, method: str, data: dict[str, Any]) -> Any:
        return self.post_process(
            self.session.post(
                f"{self.url}/api/method/{method}/", data=self.preprocess(data)
            )
        )


class CustomFrappeException(Exception):
    def __init__(self, *args: object):
        if len(args) == 1 and isinstance(args[0], str):
            try:  # Try to parse traceback from server
                args = json.loads(args[0])[0]
            except json.decoder.JSONDecodeError:
                pass
        super().__init__(args)


frappeclient.frappeclient.FrappeException = CustomFrappeException


def send_to_server(
    config: Config, customer_name: str, vk_url: str, item_codes: list[str]
):
    client = CustomFrappeClient(
        url=config.url, api_key=config.api_key, api_secret=config.api_secret
    )
    return client.post_json(
        "comfort.integrations.browser_ext.main",
        data={
            "customer_name": customer_name,
            "vk_url": vk_url,
            "item_codes": item_codes,
        },
    )


class Arguments(Namespace):
    customer_name: str
    vk_url: str
    html: str


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


def parse_args(args: list[str]):
    parser = ArgumentParser()
    parser.add_argument("customer_name", type=str)
    parser.add_argument("vk_url", type=str)
    parser.add_argument("html", type=str)
    return parser.parse_args(args, Arguments)


def main():
    config = get_config(os.path.dirname(__file__))
    init_sentry(config)
    args = parse_args(sys.argv[1:])
    item_codes = get_item_codes(args.html)
    url = send_to_server(config, args.customer_name, args.vk_url, item_codes)
    return check_call(["open", url])


if __name__ == "__main__":
    raise SystemExit(main())
