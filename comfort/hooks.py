from comfort.comfort_core.hooks import get_standard_queries as _get_standard_queries
from comfort.comfort_core.hooks import load_metadata as _load_metadata

app_name, app_title, app_description, app_publisher = _load_metadata()
standard_queries = _get_standard_queries(
    ("Customer", "Item", "Purchase Order", "Sales Order")
)

fixtures = [
    {"doctype": "Role", "filters": {"role_name": "Comfort User"}},
    {"doctype": "Custom DocPerm", "filters": {"role": "Comfort User"}},
]

after_install = "comfort.comfort_core.hooks.after_install"
boot_session = "comfort.comfort_core.hooks.extend_boot_session"
override_doctype_class = {"DocType": "comfort.comfort_core.hooks.CustomDocType"}

app_include_js = "/assets/comfort/js/index.js"

treeviews = ["Account"]
