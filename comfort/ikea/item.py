import asyncio
import os
from io import BytesIO

import aiohttp
import frappe
from comfort.ikea.utils import extract_item_codes, get_item_codes_from_ingka_pagelinks
from frappe.utils import parse_json
from ikea_api.endpoints.item.item_iows import WrongItemCodeError
from ikea_api_extender import get_items_immortally
from PIL import Image

# TODO: Download images


@frappe.whitelist()
def fetch_new_items(item_codes, force_update=False, download_images=True):
    force_update = parse_json(force_update)
    download_images = parse_json(download_images)

    if isinstance(item_codes, str):
        if "ingka.page.link/[0-9A-z]+" in item_codes:
            item_codes = get_item_codes_from_ingka_pagelinks(item_codes)
        else:
            item_codes = extract_item_codes(item_codes)

    items_to_fetch, items_already_exist = [], []
    for d in item_codes:  # TODO: Make it in bulk mode
        if frappe.db.exists("Item", d):
            items_already_exist.append(d)
            if force_update:
                items_to_fetch.append(d)
        else:
            items_to_fetch.append(d)

    res = {
        "fetched": [],
        "already_exist": items_already_exist,
        "unsuccessful": [],
        "successful": item_codes,
    }
    if len(items_to_fetch) == 0:
        return res

    try:
        response = get_items_immortally(items_to_fetch)
    except WrongItemCodeError:
        frappe.throw("Неверный артикул")

    parsed_items = response["items"]
    res["unsuccessful"] = response["unsuccessful"]
    res["fetched_items"] = response["fetched"]
    res["successful"] = [d for d in item_codes if d not in res["unsuccessful"]]
    # if download_images:
    #     # TODO: No need to download every time
    #     images = download_items_images(parsed_items)
    #     for d in parsed_items:
    #         d.image = images[d.item_code]

    for d in parsed_items:
        add_item(d, force_update=force_update)

    return res


def download_items_images(items):
    async def main(items):
        async def fetch(session, item):
            if not item.image_url:
                return item.item_code, None

            async with session.get(item.image_url, allow_redirects=0) as r:
                raw_content = await r.content.read()

            image = Image.open(BytesIO(raw_content))
            file_name = "/" + item.image_url.rsplit("/", 1)[1]
            path = "/".join(("items", item.item_code))
            full_path = os.path.abspath(frappe.get_site_path("public", path))
            frappe.create_folder(full_path)
            image.save(full_path + file_name)
            return item.item_code, "/" + path + file_name

        async def fetch_all(session, items):
            tasks = []
            loop = asyncio.get_event_loop()
            for item in items:
                task = loop.create_task(fetch(session, item))
                tasks.append(task)
            results = await asyncio.gather(*tasks)
            return results

        async with aiohttp.ClientSession() as session:
            res = await fetch_all(session, items)
            return res

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res_list = loop.run_until_complete(main(items))
    res = {}
    for i in res_list:
        if i:
            res[i[0]] = i[1]
    return res


def add_item(item, force_update):
    make_item_category(item.group_name, item.group_url)
    # raise Exception(item.__dict__)
    if item.is_combination:
        response = fetch_new_items(
            [d["item_code"] for d in item.bundle_items], force_update=force_update
        )
        for d in response["unsuccessful"]:
            _make_item(d["item_code"], d["item_name"], d["weight"])
    _make_item(
        item.item_code,
        item.name,
        item.weight,
        item.group_name,
        item.price,
        item.url,
        item.bundle_items,
    )


def make_item_category(name, url):
    if not frappe.db.exists("Item Category", name):
        return frappe.get_doc(
            {"doctype": "Item Category", "item_category_name": name, "url": url}
        ).insert()


def _make_item(
    item_code, item_name, weight, item_category=None, rate=0, url=None, child_items=[]
):
    if frappe.db.exists("Item", item_code):
        doc = frappe.get_doc("Item", item_code)
        doc.item_name = item_name
        categories = [d.item_category for d in doc.item_categories]
        if item_category not in categories:
            doc.append("item_categories", {"item_category": item_category})
        doc.url = url
        doc.rate = rate
        doc.weight = weight
        if child_items and len(child_items) > 0:
            cur_child_items = [
                {"item_code": d.item_code, "qty": d.qty} for d in doc.child_items
            ]
            new_child_items = [
                {"item_code": d["item_code"], "qty": d["qty"]} for d in child_items
            ]
            if len([d for d in cur_child_items if d not in new_child_items]) > 0:
                doc.child_items = []
                doc.extend("child_items", child_items)
        doc.save()
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_name,
                "url": url,
                "rate": rate,
                "weight": weight,
                "child_items": child_items,
            }
        )
        if item_category:
            doc.append("item_categories", {"item_category": item_category})
        doc.insert()
    return doc
