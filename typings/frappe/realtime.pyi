"""
This type stub file was generated by pyright.
"""

import frappe

redis_server = ...

@frappe.whitelist()
def get_pending_tasks_for_doc(doctype, docname): ...
def publish_progress(percent, title=..., doctype=..., docname=..., description=...): ...
def publish_realtime(
    event=...,
    message=...,
    room=...,
    user=...,
    doctype=...,
    docname=...,
    task_id=...,
    after_commit=...,
):  # -> None:
    """Publish real-time updates

    :param event: Event name, like `task_progress` etc. that will be handled by the client (default is `task_progress` if within task or `global`)
    :param message: JSON message object. For async must contain `task_id`
    :param room: Room in which to publish update (default entire site)
    :param user: Transmit to user
    :param doctype: Transmit to doctype, docname
    :param docname: Transmit to doctype, docname
    :param after_commit: (default False) will emit after current transaction is committed"""
    ...

def emit_via_redis(event, message, room):  # -> None:
    """Publish real-time updates via redis

    :param event: Event name, like `task_progress` etc.
    :param message: JSON message object. For async must contain `task_id`
    :param room: name of the room"""
    ...

def get_redis_server():  # -> Redis[bytes]:
    """returns redis_socketio connection."""
    ...

@frappe.whitelist(allow_guest=True)
def can_subscribe_doc(doctype, docname): ...
@frappe.whitelist(allow_guest=True)
def get_user_info(): ...
def get_doc_room(doctype, docname): ...
def get_user_room(user): ...
def get_site_room(): ...
def get_task_progress_room(task_id): ...
def get_chat_room(room): ...
