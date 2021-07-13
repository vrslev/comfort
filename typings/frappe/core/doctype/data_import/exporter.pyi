"""
This type stub file was generated by pyright.
"""

import typing

class Exporter:
    def __init__(
        self,
        doctype,
        export_fields=...,
        export_data=...,
        export_filters=...,
        export_page_length=...,
        file_type=...,
    ) -> None:
        """
        Exports records of a DocType for use with Importer
                :param doctype: Document Type to export
                :param export_fields=None: One of 'All', 'Mandatory' or {'DocType': ['field1', 'field2'], 'Child DocType': ['childfield1']}
                :param export_data=False: Whether to export data as well
                :param export_filters=None: The filters (dict or list) which is used to query the records
                :param file_type: One of 'Excel' or 'CSV'
        """
        ...
    def get_all_exportable_fields(self): ...
    def serialize_exportable_fields(self): ...
    def get_exportable_fields(self, doctype, fieldnames): ...
    def get_data_to_export(self): ...
    def add_data_row(self, doctype, parentfield, doc, rows, row_idx): ...
    def get_data_as_docs(self): ...
    def add_header(self): ...
    def add_data(self): ...
    def get_csv_array(self): ...
    def get_csv_array_for_export(self): ...
    def build_response(self): ...
    def build_csv_response(self): ...
    def build_xlsx_response(self): ...
    def group_children_data_by_parent(self, children_data: typing.Dict[str, list]): ...
