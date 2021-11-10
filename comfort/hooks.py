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
    {
        "doctype": "Property Setter",
        "filters": {
            "name": (
                "in",
                (
                    "Purchase Order-main-default_print_format",
                    "Sales Order-main-default_print_format",
                ),
            )
        },
    },
]

after_install = "comfort.comfort_core.hooks.after_install"
after_migrate = "comfort.comfort_core.hooks.after_migrate"
boot_session = "comfort.comfort_core.hooks.extend_boot_session"
override_doctype_class = {"DocType": "comfort.comfort_core.hooks.CustomDocType"}

app_include_js = "/assets/js/comfort.min.js"
web_include_js = "/assets/js/comfort-web.min.js"

treeviews = ["Account"]

global_search_doctypes = _get_global_search_doctypes()

reqd_frappe_version = "v13.14.0"

scheduler_events = {
    "weekly": [
        "comfort.entities.doctype.customer.customer.update_all_customers_from_vk"
    ],
}

get_translated_dict = {("boot", None): "comfort.translations.get_translated_dict"}

jenv = {
    "methods": [
        "format_item_code:comfort.integrations.ikea.format_item_code",
        "format_money:frappe.utils.formatters.fmt_money",
        "format_phone:comfort.queries.format_phone",
    ],
}
