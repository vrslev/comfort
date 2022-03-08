import os
import os.path
from typing import Any

from uvicorn.middleware.wsgi import WSGIMiddleware
from werkzeug.middleware.shared_data import SharedDataMiddleware

import comfort.utils  # type: ignore # Initialise Sentry and patches
import frappe
import frappe.app
from frappe.utils.bench_helper import get_sites


def _get_asgi_app():
    _app: Any = frappe.app.application

    with frappe.init_site():
        # Some code so uvicorn could be used in development:
        # - Set current site to first site (like `bench serve does`)
        # - Add /assets and /files endpoint
        if frappe.conf.developer_mode:
            frappe.app._site = get_sites(None)[0]

            sites_path: str = frappe.local.sites_path

            _app = SharedDataMiddleware(  # TODO: THIS IS WRONG Shared and Static are different
                app=_app,
                exports={
                    "/assets": os.path.join(sites_path, "assets"),
                    "/files": os.path.abspath(sites_path),
                },
            )

    return WSGIMiddleware(_app)


app = _get_asgi_app()
