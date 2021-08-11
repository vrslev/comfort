from frappe.core.doctype.doctype.doctype import DocType as _DocType
from frappe.modules import make_boilerplate


class DocType(_DocType):
    def make_controller_template(self):
        """Do not madly create dt.js, test_dt.py files"""
        make_boilerplate("controller._py", self)
