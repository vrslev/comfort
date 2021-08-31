from comfort.comfort_core.hooks import get_standard_queries, load_metadata

app_name, app_title, app_description, app_publisher = load_metadata()
standard_queries = get_standard_queries(
    ("Customer", "Item", "Purchase Order", "Sales Order")
)

before_install = "comfort.comfort_core.hooks.before_install"
after_install = "comfort.comfort_core.hooks.after_install"
boot_session = "comfort.comfort_core.hooks.extend_boot_session"
override_doctype_class = {"DocType": "comfort.comfort_core.hooks.CustomDocType"}

app_include_js = "/assets/comfort/js/index.js"

treeviews = ["Account"]
