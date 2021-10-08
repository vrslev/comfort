from comfort.comfort_core.hooks import (
    get_global_search_doctypes as _get_global_search_doctypes,
)
from comfort.comfort_core.hooks import load_metadata as _load_metadata
from comfort.queries import get_standard_queries as _get_standard_queries

app_name, app_title, app_description, app_publisher, app_version = _load_metadata()
standard_queries = _get_standard_queries(
    ("Customer", "Item", "Purchase Order", "Sales Order")
)

fixtures = [
    {"doctype": "Role", "filters": {"role_name": "Comfort User"}},
    {"doctype": "Custom DocPerm", "filters": {"role": "Comfort User"}},
    {"doctype": "Module Profile", "filters": {"name": "Comfort Module Profile"}},
    {"doctype": "Block Module", "filters": {"parent": "Comfort Module Profile"}},
]

after_install = "comfort.comfort_core.hooks.after_install"
boot_session = "comfort.comfort_core.hooks.extend_boot_session"
override_doctype_class = {"DocType": "comfort.comfort_core.hooks.CustomDocType"}

app_include_js = "/assets/js/comfort.min.js"
web_include_js = "/assets/js/comfort-web.min.js"

treeviews = ["Account"]

global_search_doctypes = _get_global_search_doctypes()

reqd_frappe_version = "v13.12.1"
