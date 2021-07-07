import frappe
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.utils import unique


def get_fields(doctype, fields=None):
    # From ERPNext
    if fields is None:
        fields = []
    meta = frappe.get_meta(doctype)
    fields.extend(meta.get_search_fields())

    if meta.title_field and not meta.title_field.strip() in fields:
        fields.insert(1, meta.title_field.strip())

    return unique(fields)


def format_money(money):
    return f"{int(money)} ₽"


def format_weight(weight):
    return f"{float(weight)} кг"


def format_item_query(d):
    if d[2]:
        d[2] = format_money(d[2])


def format_purchase_order_query(d):
    if d[2]:
        d[2] = format_money(d[2])
    if d[3]:
        d[3] = format_weight(d[3])


def format_sales_order_query(d):
    if d[3]:
        d[3] = format_money(d[3])


QUERY_FORMATTERS = {
    "Item": format_item_query,
    "Purchase Order": format_purchase_order_query,
    "Sales Order": format_sales_order_query,
}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def default_query(doctype, txt, searchfield, start, page_len, filters):
    conditions = []
    fields = get_fields(doctype, ["name"])

    query = frappe.db.sql(
        f"""
        SELECT {", ".join(fields)} FROM `tab{doctype}`
        WHERE {searchfield} LIKE %(txt)s
        {get_filters_cond(doctype, filters, conditions)}
        {get_match_cond(doctype)}

        ORDER BY modified DESC
        LIMIT {start}, {page_len}
        """,
        {"txt": "%%%s%%" % txt},
        as_list=True,
    )
    if doctype in QUERY_FORMATTERS:
        for d in query:
            QUERY_FORMATTERS[doctype](d)
    return query
