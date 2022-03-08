import pytest

from comfort.comfort_core import CommissionSettings
from comfort.utils import get_doc
from frappe import ValidationError


def test_validate_last_to_amount_is_zero_raises_on_not_zero(
    commission_settings: CommissionSettings,
):
    commission_settings.ranges[-1].to_amount = 300
    with pytest.raises(ValidationError, match="To Amount in last row should be zero"):
        commission_settings.validate_last_to_amount_is_zero()


def test_validate_to_amounts_are_not_zero_not_raise_on_last_row(
    commission_settings: CommissionSettings,
):
    commission_settings.ranges[-1].to_amount = 0
    commission_settings.validate_to_amounts_are_not_zero()


@pytest.mark.parametrize("range_idx", (0, 1))
def test_validate_to_amounts_are_not_zero_raises_on_zero_amount(
    commission_settings: CommissionSettings, range_idx: int
):
    commission_settings.ranges[range_idx].to_amount = 0

    with pytest.raises(
        ValidationError, match="To Amount shouldn't be zero except last row"
    ):
        commission_settings.validate_to_amounts_are_not_zero()


def test_validate_to_amounts_are_not_zero_raises_on_zero_percentage(
    commission_settings: CommissionSettings,
):
    commission_settings.ranges[0].percentage = 0

    with pytest.raises(ValidationError, match="Percentage shouldn't be zero"):
        commission_settings.validate_to_amounts_are_not_zero()


@pytest.mark.parametrize("to_amount", (200, 300))
def test_validate_to_amounts_order_raises_on_wrong_order(
    commission_settings: CommissionSettings, to_amount: int
):
    commission_settings.ranges[0].to_amount = to_amount
    with pytest.raises(
        ValidationError, match="To Amounts should be in ascending order"
    ):
        commission_settings.validate_to_amounts_order()


def test_validate_to_amounts_order_not_raises(commission_settings: CommissionSettings):
    commission_settings.validate_to_amounts_order()


def test_set_from_amounts(commission_settings: CommissionSettings):
    commission_settings.set_from_amounts()

    previous_to_amount = -1
    for range_ in commission_settings.ranges:
        assert range_.from_amount == previous_to_amount + 1
        previous_to_amount = range_.to_amount


def test_commission_settings_validate_empty_doc():
    doc = get_doc(CommissionSettings)
    doc.validate()


@pytest.mark.parametrize(
    "amount,expected_percentage",
    ((50, 20), (100, 20), (101, 15), (150, 15), (200, 15), (500, 10)),
)
def test_get_commission_percentage_passes(
    commission_settings: CommissionSettings, amount: int, expected_percentage: int
):
    commission_settings.insert()
    assert commission_settings.get_commission_percentage(amount) == expected_percentage


def test_get_commission_percentage_raises_on_negative_number(
    commission_settings: CommissionSettings,
):
    commission_settings.insert()
    with pytest.raises(ValidationError, match="Amount should be more that zero"):
        commission_settings.get_commission_percentage(-100)


def test_get_commission_percentage_raises_on_none(
    commission_settings: CommissionSettings,
):
    commission_settings.insert()
    with pytest.raises(ValidationError, match="Amount should be more that zero"):
        commission_settings.get_commission_percentage(None)
