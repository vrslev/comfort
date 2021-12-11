from __future__ import annotations

from base_telegram_bot import BaseTelegramBot

from comfort import get_all
from comfort.integrations.tracking import russian_post, vozovoz
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder

purchases = get_all(
    PurchaseOrder,
    filters={
        "status": "To Receive",
        "supplier_name": ("in", ("Russian Post", "Vozovoz")),
    },
    fields=("name", "supplier_name", "supplier_tracking_no"),
)
tracking_no_to_purchase_names = {p.supplier_tracking_no: p.name for p in purchases}

responses: list[russian_post.TrackingItem | vozovoz.Response] = []
for purchase in purchases:
    if purchase.supplier_name == "Russian Post":
        responses.append(russian_post.track(purchase.supplier_tracking_no))
    elif purchase.supplier_name == "Vozovoz":
        responses.append(vozovoz.track(purchase.supplier_tracking_no))

print(responses)
arrived_purchase_names = [
    tracking_no_to_purchase_names[r.barcode] for r in responses if r.is_arrived()
]
print(arrived_purchase_names)


class Bot(BaseTelegramBot):
    def send_message(self, *, chat_id: int, text: str):
        self.make_request(
            method="/sendMessage", json={"chat_id": chat_id, "text": text}
        )


Bot("").send_message(
    chat_id=0, text=f"Пришли заказы: {', '.join(arrived_purchase_names)}"
)
