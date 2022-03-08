from __future__ import annotations

from comfort.utils import TypedDocument, ValidationError, _, get_cached_doc

from ..commission_range.commission_range import CommissionRange


class CommissionSettings(TypedDocument):
    ranges: list[CommissionRange]

    def validate_last_to_amount_is_zero(self):
        if not self.ranges[-1].to_amount == 0:
            raise ValidationError(_("To Amount in last row should be zero"))

    def validate_to_amounts_are_not_zero(self):
        for c in self.ranges[:-1]:
            if c.to_amount == 0:
                raise ValidationError(_("To Amount shouldn't be zero except last row"))
            if c.percentage == 0:
                raise ValidationError(_("Percentage shouldn't be zero"))

    def validate_to_amounts_order(self):
        for idx, c in enumerate(self.ranges[:-2]):
            if c.to_amount >= self.ranges[idx + 1].to_amount:
                raise ValidationError(_("To Amounts should be in ascending order"))

    def set_from_amounts(self):
        previous_to_amount = -1
        for range_ in self.ranges:
            range_.from_amount = previous_to_amount + 1
            previous_to_amount = range_.to_amount

    def validate(self):
        if not self.ranges:
            return

        self.validate_to_amounts_are_not_zero()
        self.validate_last_to_amount_is_zero()
        self.validate_to_amounts_order()
        self.set_from_amounts()

    def on_change(self):
        self.clear_cache()

    @staticmethod
    def get_commission_percentage(amount: float | int | None):
        if not amount or amount < 0:
            raise ValidationError(_("Amount should be more that zero"))

        doc = get_cached_doc(CommissionSettings)
        ranges = doc.ranges.copy()
        ranges.reverse()
        from_amounts_to_percentage = {r.from_amount: r.percentage for r in ranges}

        for from_amount, percentage in from_amounts_to_percentage.items():
            if amount >= from_amount:
                return percentage

        # Called when no Commission Settings in system
        # Not covered because it is expensive
        raise ValidationError(_("No satisfying commission found"))  # pragma: no cover
