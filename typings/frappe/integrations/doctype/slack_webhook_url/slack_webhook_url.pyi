"""
This type stub file was generated by pyright.
"""

from frappe.model.document import Document

error_messages = ...

class SlackWebhookURL(Document): ...

def send_slack_message(webhook_url, message, reference_doctype, reference_name): ...
