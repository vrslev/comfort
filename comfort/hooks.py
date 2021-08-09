from comfort.fixtures.hooks import get_standard_queries, load_metadata

# Load required metadata from pyproject.toml
app_name, app_title, app_description, app_publisher = load_metadata()

# Include in index.html
app_include_js = "/assets/comfort/js/index.js"

# Create accounts after site install
after_install = "comfort.fixtures.hooks.after_install"

# Extend boot session with currency information
boot_session = "comfort.fixtures.hooks.boot_session"

# Export fixtures
fixtures = ["List View Settings"]

# Default queries for Comfort doctypes
standard_queries = get_standard_queries(
    ["Customer", "Item", "Purchase Order", "Sales Order"]
)

# Treeviews by default in listed doctypes
treeviews = ["Account"]
