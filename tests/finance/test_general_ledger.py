import pytest

import frappe
from comfort import copy_doc
from comfort.finance import GLEntry
from comfort.finance.report.general_ledger.general_ledger import (
    get_data,
    validate_filters,
)
from frappe.utils import add_to_date, get_date_str, today


def test_gl_validate_filters_raises():
    filters: dict[str, str] = {
        "from_date": "2021-08-31",
        "to_date": "2021-07-31",
    }
    with pytest.raises(
        frappe.ValidationError, match="To Date should be after From Date"
    ):
        validate_filters(filters)


def test_gl_validate_filters_passes():
    filters: dict[str, str] = {
        "from_date": "2021-07-31",
        "to_date": "2021-08-31",
    }
    validate_filters(filters)


def insert_gl_entries_with_wrong_conditions(gl_entry: GLEntry):
    gl_entry.db_insert()
    new_doc: GLEntry = copy_doc(gl_entry)
    new_doc.docstatus = 2
    new_doc.db_insert()
    new_doc2: GLEntry = copy_doc(gl_entry)
    new_doc2.creation = add_to_date("2021-07-31", days=-50)
    new_doc2.db_insert()


def test_gl_get_data(gl_entry: GLEntry):
    insert_gl_entries_with_wrong_conditions(gl_entry)
    filters: dict[str, str] = {
        "from_date": "2021-07-31",
        "to_date": get_date_str(today()),
    }
    data = get_data(filters)
    assert len(data) == 1
    assert data[0].gl_entry == gl_entry.name
