"""
This type stub file was generated by pyright.
"""

from frappe.model.document import Document

class Language(Document):
    def validate(self): ...
    def before_rename(self, old, new, merge=...): ...

def validate_with_regex(name, label): ...
def export_languages_json():  # -> None:
    """Export list of all languages"""
    ...

def sync_languages():  # -> None:
    """Sync frappe/geo/languages.json with Language"""
    ...

def update_language_names():  # -> None:
    """Update frappe/geo/languages.json names (for use via patch)"""
    ...
