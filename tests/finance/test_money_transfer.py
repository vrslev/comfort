import pytest

from comfort import get_all, new_doc
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.finance.doctype.money_transfer.money_transfer import MoneyTransfer
from frappe import ValidationError


@pytest.fixture
@pytest.mark.usefixtures("accounts")
def money_transfer():
    doc = new_doc(MoneyTransfer)
    doc.from_account = "Cash"
    doc.to_account = "Bank"
    doc.amount = 1150
    return doc


def test_money_transfer_validate_raises(money_transfer: MoneyTransfer):
    money_transfer.to_account = money_transfer.from_account
    with pytest.raises(
        ValidationError, match="From Account and To Account shouldn't be the same"
    ):
        money_transfer.validate()


def test_money_transfer_validate_passes(money_transfer: MoneyTransfer):
    money_transfer.validate()


def test_money_transfer_before_submit(money_transfer: MoneyTransfer):
    money_transfer.insert()
    money_transfer.before_submit()
    gl_entries = get_all(
        GLEntry,
        fields=("account", "debit", "credit"),
        filters={
            "voucher_type": money_transfer.doctype,
            "voucher_no": money_transfer.name,
        },
    )

    assert {e.account: (e.debit, e.credit) for e in gl_entries} == {
        money_transfer.from_account: (0, money_transfer.amount),
        money_transfer.to_account: (money_transfer.amount, 0),
    }
