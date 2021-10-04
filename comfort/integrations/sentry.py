import os
from importlib.metadata import distribution
from logging import Logger
from typing import Callable, TypedDict

import redis.exceptions
import sentry_sdk
import sentry_sdk.integrations.wsgi
from sentry_sdk.integrations.logging import ignore_logger
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.rq import RqIntegration
from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware
from werkzeug.wrappers.response import Response

import frappe
import frappe.app


class _GetSentryInfoPayload(TypedDict):
    dsn: str
    release: str


@frappe.whitelist()
def get_info() -> _GetSentryInfoPayload:
    return {
        "dsn": os.environ["SENTRY_DSN"],
        "release": f"comfort@{distribution('comfort').metadata['Version']}",
    }


def _init_sentry():
    info = get_info()
    sentry_sdk.init(
        dsn=info["dsn"],
        release=info["release"],
        integrations=[RedisIntegration(), RqIntegration()],
        traces_sample_rate=1.0,
        ignore_errors=[redis.exceptions.ConnectionError],
    )


def _add_wsgi_integration():
    frappe.app.application = SentryWsgiMiddleware(frappe.app.application)  # type: ignore


def _patch_router_exception_handler():
    def add_frappe_logger_to_disabled():
        logger_to_disable: Logger = frappe.logger()
        ignore_logger(logger_to_disable.name)

    old_handle_exception: Callable[[Exception], Response] = frappe.app.handle_exception  # type: ignore

    def handle_exception(e: Exception):
        add_frappe_logger_to_disabled()  # Ensure noisy Frappe logger doesn't interrupt
        # Handle error, if there's issue, Sentry's WSGI integration will handle it:
        response: Response = old_handle_exception(e)
        # Otherwise, handle it here:
        sentry_sdk.capture_exception(e)
        return response

    frappe.app.handle_exception = handle_exception


def init():
    if os.environ.get("SENTRY_DSN"):
        _init_sentry()
        _add_wsgi_integration()
        _patch_router_exception_handler()
