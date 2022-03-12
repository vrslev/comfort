from typing import Literal

from comfort.finance.utils import create_gl_entry
from comfort.utils import TypedDocument, ValidationError, _


class MoneyTransfer(TypedDocument):
    doctype: Literal["Money Transfer"]

    amount: int
    from_account: str
    to_account: str

    def validate(self):
        if self.from_account == self.to_account:
            raise ValidationError(
                _("From Account and To Account shouldn't be the same")
            )

    def before_submit(self) -> None:
        create_gl_entry(self.doctype, self.name, self.from_account, 0, self.amount)
        create_gl_entry(self.doctype, self.name, self.to_account, self.amount, 0)
