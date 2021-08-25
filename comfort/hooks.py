from comfort.comfort_core.hooks.metadata import load_metadata
from comfort.comfort_core.hooks.queries import get_standard_queries

app_name, app_title, app_description, app_publisher = load_metadata()

standard_queries = get_standard_queries(
    ("Customer", "Item", "Purchase Order", "Sales Order")
)

after_install = "comfort.finance.chart_of_accounts.initialize_accounts"
boot_session = "comfort.comfort_core.hooks.boot.extend_boot_session_with_currency"
override_doctype_class = {"DocType": "comfort.comfort_core.hooks.overrides.DocType"}

app_include_js = "/assets/comfort/js/index.js"

treeviews = ["Account"]
