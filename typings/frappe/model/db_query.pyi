"""
This type stub file was generated by pyright.
"""

class DatabaseQuery:
    def __init__(self, doctype, user=...) -> None: ...
    def execute(
        self,
        fields=...,
        filters=...,
        or_filters=...,
        docstatus=...,
        group_by=...,
        order_by=...,
        limit_start=...,
        limit_page_length=...,
        as_list=...,
        with_childnames=...,
        debug=...,
        ignore_permissions=...,
        user=...,
        with_comment_count=...,
        join=...,
        distinct=...,
        start=...,
        page_length=...,
        limit=...,
        ignore_ifnull=...,
        save_user_settings=...,
        save_user_settings_fields=...,
        update=...,
        add_total_row=...,
        user_settings=...,
        reference_doctype=...,
        return_query=...,
        strict=...,
        pluck=...,
        ignore_ddl=...,
    ): ...
    def build_and_run(self): ...
    def prepare_args(self): ...
    def parse_args(self):  # -> None:
        """Convert fields and filters from strings to list, dicts"""
        ...
    def sanitize_fields(self):  # -> None:
        """
        regex : ^.*[,();].*
        purpose : The regex will look for malicious patterns like `,`, '(', ')', '@', ;' in each
                        field which may leads to sql injection.
        example :
                field = "`DocType`.`issingle`, version()"
        As field contains `,` and mysql function `version()`, with the help of regex
        the system will filter out this field.
        """
        ...
    def extract_tables(self):  # -> None:
        """extract tables from fields"""
        ...
    def append_table(self, table_name): ...
    def set_field_tables(self):  # -> None:
        """If there are more than one table, the fieldname must not be ambiguous.
        If the fieldname is not explicitly mentioned, set the default table"""
        ...
    def get_table_columns(self): ...
    def set_optional_columns(self):  # -> None:
        """Removes optional columns like `_user_tags`, `_comments` etc. if not in table"""
        ...
    def build_conditions(self): ...
    def build_filter_conditions(
        self, filters, conditions, ignore_permissions=...
    ):  # -> None:
        """build conditions from user filters"""
        ...
    def prepare_filter_condition(self, f):  # -> str:
        """Returns a filter condition in the format:
        ifnull(`tabDocType`.`fieldname`, fallback) operator "value"
        """
        ...
    def build_match_conditions(self, as_condition=...):  # -> str | list[Unknown]:
        """add match conditions if applicable"""
        ...
    def get_share_condition(self): ...
    def add_user_permissions(self, user_permissions): ...
    def get_permission_query_conditions(self): ...
    def set_order_by(self, args): ...
    def validate_order_by_and_group_by(self, parameters):  # -> None:
        """Check order by, group by so that atleast one column is selected and does not have subquery"""
        ...
    def add_limit(self): ...
    def add_comment_count(self, result): ...
    def update_user_settings(self): ...

def check_parent_permission(parent, child_doctype): ...
def get_order_by(doctype, meta): ...
def is_parent_only_filter(doctype, filters): ...
def has_any_user_permission_for_doctype(doctype, user, applicable_for): ...
def get_between_date_filter(value, df=...):  # -> str:
    """
    return the formattted date as per the given example
    [u'2017-11-01', u'2017-11-03'] => '2017-11-01 00:00:00.000000' AND '2017-11-04 00:00:00.000000'
    """
    ...

def get_additional_filter_field(additional_filters_config, f, value): ...
def get_date_range(operator, value): ...
