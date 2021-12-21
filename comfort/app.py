import os.path
from typing import Any

from uvicorn.middleware.wsgi import WSGIMiddleware
from werkzeug.middleware.shared_data import SharedDataMiddleware

import frappe
import frappe.app
from frappe.boot import get_bootinfo
from frappe.utils.bench_helper import get_sites


def _get_first_site():
    sites: list[str] = get_sites(None)  # type: ignore
    assert sites, "No sites found"
    return sites[0]


def _get_asgi_app():
    first_site = _get_first_site()
    _app: Any = frappe.app.application

    with frappe.init_site(first_site):
        # Load bootinfo so first startup is faster
        frappe.connect()
        get_bootinfo()

        # Some code so uvicorn could be used in development:
        # - Set current site to first site (like `bench serve does`)
        # - Add /assets and /files endpoint
        if frappe.conf.developer_mode:
            sites_path: str = frappe.local.sites_path

            _app = SharedDataMiddleware(
                app=_app,
                exports={
                    "/assets": os.path.join(sites_path, "assets"),
                    "/files": os.path.abspath(sites_path),
                },
            )
            frappe.app._site = first_site

    return WSGIMiddleware(_app)


app = _get_asgi_app()
