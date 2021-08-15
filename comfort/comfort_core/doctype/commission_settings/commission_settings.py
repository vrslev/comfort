from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ..commission_range.commission_range import CommissionRange


class CommissionSettings(Document):
    ranges: list[CommissionRange]

    def validate_last_to_amount_is_zero(self):
        if not self.ranges[-1].to_amount == 0:
            frappe.throw(_("To Amount in last row should be zero"))

    def validate_to_amounts_are_not_zero(self):
        for c in self.ranges[:-1]:
            if c.to_amount == 0:
                frappe.throw(_("To Amount shouldn't be zero except last row"))
            elif c.percentage == 0:
                frappe.throw(_("Percentage shouldn't be zero"))

    def validate_to_amounts_order(self):
        for idx, c in enumerate(self.ranges[:-2]):
            if c.to_amount > self.ranges[idx + 1].to_amount:
                frappe.throw(_("To Amounts should be in ascending order"))

    def set_from_amounts(self):
        previous_to_amount = -1
        for range_ in self.ranges:
            range_.from_amount = previous_to_amount + 1
            previous_to_amount = range_.to_amount

    def validate(self):  # pragma: no cover
        self.validate_to_amounts_are_not_zero()
        self.validate_last_to_amount_is_zero()
        self.validate_to_amounts_order()
        self.set_from_amounts()

    @staticmethod
    def get_commission_percentage(amount: float | int) -> int:
        if amount < 0:
            return frappe.throw(_("Amount should be a positive number"))

        doc: CommissionSettings = frappe.get_cached_doc(
            "Commission Settings", "Commission Settings"
        )
        ranges = doc.ranges.copy()
        ranges.reverse()
        from_amounts_to_percentage = {r.from_amount: r.percentage for r in ranges}

        for from_amount, percentage in from_amounts_to_percentage.items():
            if amount >= from_amount:
                return percentage

        frappe.throw(_("No satisfying commission found"))  # pragma: no cover