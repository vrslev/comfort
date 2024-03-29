from __future__ import annotations

from typing import Any

import sentry_sdk
from pydantic import BaseModel, Field, validator
from werkzeug import Response

import frappe
from comfort.integrations.ikea import fetch_items
from comfort.integrations.vk_api import VkApi
from comfort.transactions import SalesOrder
from comfort.utils import get_value, new_doc


class VkFormAnswer(BaseModel):
    key: str
    question: str
    answer: str


class VkFormObjectProp(BaseModel):
    lead_id: int
    group_id: int
    user_id: int
    form_id: int
    form_name: str
    answers: list[VkFormAnswer]

    @validator("group_id")
    def check_group_id(cls, v: int):
        assert v == int(get_value("Vk Form Settings", fieldname="group_id"))
        return v

    @validator("form_name")
    def check_form_name(cls, v: str):
        assert v == "Оформить заказ"
        return v


class VkForm(BaseModel):
    type: str
    object: VkFormObjectProp
    group_id: int
    event_id: str
    secret: str

    @validator("type")
    def check_type(cls, v: str):
        assert v == "lead_forms_new"
        return v

    @validator("secret")
    def check_secret(cls, v: str):
        assert v == get_value("Vk Form Settings", fieldname="api_secret")
        return v


def _get_mapped_answers(answers: list[VkFormAnswer]):
    return Answers(**{a.key: a.answer for a in answers})


def _get_customer_name(first_name: str, last_name: str):
    if last_name:
        return f"{first_name} {last_name}"
    return first_name


def _create_vk_group_dialog_url(group_id: int, user_id: int) -> str:
    return f"https://vk.com/gim{group_id}?sel={user_id}"


def _create_customer(first_name: str, last_name: str, group_id: int, user_id: int):
    from comfort.integrations.browser_ext import _create_customer

    name = _get_customer_name(first_name, last_name)
    vk_url = _create_vk_group_dialog_url(group_id, user_id)
    return _create_customer(name, vk_url)


class Answers(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    raw_order: str = Field(alias="custom_0")
    raw_delivery_type: str = Field(alias="custom_1")


def _get_delivery_service(raw_delivery_type: str):
    if "подъезд" in raw_delivery_type:
        return {"type": "Delivery to Entrance", "rate": 150}
    elif "квартир" in raw_delivery_type:
        return {"type": "Delivery to Apartment", "rate": 400}


def _create_sales_order(
    customer_name: str, raw_order: str, raw_delivery_type: str
) -> None:
    fetch_result = fetch_items(raw_order, force_update=True)
    if not fetch_result["successful"]:
        return

    doc = new_doc(SalesOrder)
    doc.customer = customer_name
    doc.extend(
        "items",
        [
            {"item_code": item_code, "qty": 1}
            for item_code in fetch_result["successful"]
        ],
    )
    if delivery_service := _get_delivery_service(raw_delivery_type):
        doc.append("services", delivery_service)

    doc.save()


def _send_confirmation_message(user_id: int, first_name: str) -> None:
    message = f"{first_name}, спасибо за ваш заказ! Когда обработаем его, напишем вам!"
    VkApi().send_message(user_id=user_id, message=message)


def process_form(form: dict[Any, Any]) -> None:
    response = VkForm(**form)
    answers = _get_mapped_answers(response.object.answers)

    customer = _create_customer(
        answers.first_name,
        answers.last_name,
        response.object.group_id,
        response.object.user_id,
    )
    _create_sales_order(customer.name, answers.raw_order, answers.raw_delivery_type)
    frappe.db.commit()
    _send_confirmation_message(
        user_id=response.object.user_id, first_name=answers.first_name
    )


@frappe.whitelist(allow_guest=True)
def main():
    frappe.session.user = frappe.session.sid = "Administrator"
    try:
        process_form(frappe.form_dict)  # type: ignore
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
    return Response("ok")
