import pytest

from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from frappe import ValidationError


@pytest.mark.parametrize("v", ("Assets", "Liabilities", "Expense", "Income", "Service"))
def test_gl_entry_validate_raises(gl_entry: GLEntry, v: str):
    gl_entry.account = v
    with pytest.raises(ValidationError, match="Can't add GL Entry for group account"):
        gl_entry.validate()


def test_gl_entry_validate_passes(gl_entry: GLEntry):
    gl_entry.account = "Cash"
    gl_entry.validate()
