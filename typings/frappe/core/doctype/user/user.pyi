"""
This type stub file was generated by pyright.
"""

import frappe
from frappe.model.document import Document
from frappe.rate_limiter import rate_limit
from frappe.utils.password import get_password_reset_limit

STANDARD_USERS = ...

class MaxUsersReachedError(frappe.ValidationError): ...

class User(Document):
    __new_password = ...
    def __setup__(self): ...
    def autoname(self):  # -> None:
        """set name as Email Address"""
        ...
    def onload(self): ...
    def before_insert(self): ...
    def after_insert(self): ...
    def validate(self): ...
    def validate_roles(self): ...
    def validate_allowed_modules(self): ...
    def validate_user_image(self): ...
    def on_update(self): ...
    def has_website_permission(self, ptype, user, verbose=...):
        """Returns true if current user is the session user"""
        ...
    def check_demo(self): ...
    def set_full_name(self): ...
    def check_enable_disable(self): ...
    def add_system_manager_role(self): ...
    def email_new_password(self, new_password=...): ...
    def set_system_user(self):  # -> None:
        """For the standard users like admin and guest, the user type is fixed."""
        ...
    def set_roles_and_modules_based_on_user_type(self): ...
    def has_desk_access(self):  # -> int | Literal[False]:
        """Return true if any of the set roles has desk access"""
        ...
    def share_with_self(self): ...
    def validate_share(self, docshare): ...
    def send_password_notification(self, new_password): ...
    @Document.hook
    def validate_reset_password(self): ...
    def reset_password(self, send_email=..., password_expired=...): ...
    def get_other_system_managers(self): ...
    def get_fullname(self):  # -> str:
        """get first_name space last_name"""
        ...
    def password_reset_mail(self, link): ...
    def send_welcome_mail_to_user(self): ...
    def send_login_mail(self, subject, template, add_args, now=...):  # -> None:
        """send mail with login details"""
        ...
    def a_system_manager_should_exist(self): ...
    def on_trash(self): ...
    def before_rename(self, old_name, new_name, merge=...): ...
    def validate_rename(self, old_name, new_name): ...
    def validate_email_type(self, email): ...
    def after_rename(self, old_name, new_name, merge=...): ...
    def append_roles(self, *roles):  # -> None:
        """Add roles to user"""
        ...
    def add_roles(self, *roles):  # -> None:
        """Add roles to user and save"""
        ...
    def remove_roles(self, *roles): ...
    def remove_all_roles_for_guest(self): ...
    def remove_disabled_roles(self): ...
    def ensure_unique_roles(self): ...
    def validate_username(self): ...
    def password_strength_test(self):  # -> None:
        """test password strength"""
        ...
    def suggest_username(self): ...
    def username_exists(self, username=...): ...
    def get_blocked_modules(self):  # -> list[Unknown]:
        """Returns list of modules blocked for that user"""
        ...
    def validate_user_email_inbox(self):  # -> None:
        """check if same email account added in User Emails twice"""
        ...
    def get_social_login_userid(self, provider): ...
    def set_social_login_userid(self, provider, userid, username=...): ...
    def get_restricted_ip_list(self): ...
    @classmethod
    def find_by_credentials(
        cls, user_name: str, password: str, validate_password: bool = ...
    ):  # -> None:
        """Find the user by credentials.

        This is a login utility that needs to check login related system settings while finding the user.
        1. Find user by email ID by default
        2. If allow_login_using_mobile_number is set, you can use mobile number while finding the user.
        3. If allow_login_using_user_name is set, you can use username while finding the user.
        """
        ...

@frappe.whitelist()
def get_timezones(): ...
@frappe.whitelist()
def get_all_roles(arg=...):  # -> list[Unknown]:
    """return all roles"""
    ...

@frappe.whitelist()
def get_roles(arg=...):
    """get roles for a user"""
    ...

@frappe.whitelist()
def get_perm_info(role):
    """get permission info"""
    ...

@frappe.whitelist(allow_guest=True)
def update_password(
    new_password, logout_all_sessions=..., key=..., old_password=...
): ...
@frappe.whitelist(allow_guest=True)
def test_password_strength(new_password, key=..., old_password=..., user_data=...): ...
@frappe.whitelist()
def has_email_account(email): ...
@frappe.whitelist(allow_guest=False)
def get_email_awaiting(user): ...
@frappe.whitelist(allow_guest=False)
def set_email_password(email_account, user, password): ...
def setup_user_email_inbox(
    email_account, awaiting_password, email_id, enable_outgoing
):  # -> None:
    """setup email inbox for user"""
    ...

def remove_user_email_inbox(email_account):  # -> None:
    """remove user email inbox settings if email account is deleted"""
    ...

def ask_pass_update(): ...
def reset_user_data(user): ...
@frappe.whitelist()
def verify_password(password): ...
@frappe.whitelist(allow_guest=True)
def sign_up(email, full_name, redirect_to): ...
@frappe.whitelist(allow_guest=True)
@rate_limit(
    key="user", limit=get_password_reset_limit, seconds=24 * 60 * 60, methods=["POST"]
)
def reset_password(user): ...
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def user_query(doctype, txt, searchfield, start, page_len, filters): ...
def get_total_users():  # -> Any | int | float:
    """Returns total no. of system users"""
    ...

def get_system_users(exclude_users=..., limit=...): ...
def get_active_users():  # -> Any:
    """Returns No. of system users who logged in, in the last 3 days"""
    ...

def get_website_users():  # -> Any:
    """Returns total no. of website users"""
    ...

def get_active_website_users():  # -> Any:
    """Returns No. of website users who logged in, in the last 3 days"""
    ...

def get_permission_query_conditions(user): ...
def has_permission(doc, user): ...
def notify_admin_access_to_system_manager(login_manager=...): ...
def extract_mentions(txt):  # -> list[Unknown]:
    """Find all instances of @mentions in the html."""
    ...

def handle_password_test_fail(result): ...
def update_gravatar(name): ...
@frappe.whitelist(allow_guest=True)
def send_token_via_sms(tmp_id, phone_no=..., user=...): ...
@frappe.whitelist(allow_guest=True)
def send_token_via_email(tmp_id, token=...): ...
@frappe.whitelist(allow_guest=True)
def reset_otp_secret(user): ...
def throttle_user_creation(): ...
@frappe.whitelist()
def get_role_profile(role_profile): ...
@frappe.whitelist()
def get_module_profile(module_profile): ...
def update_roles(role_profile): ...
def create_contact(user, ignore_links=..., ignore_mandatory=...): ...
@frappe.whitelist()
def generate_keys(user):  # -> dict[str, Unknown] | None:
    """
    generate api key and api secret

    :param user: str
    """
    ...

@frappe.whitelist()
def switch_theme(theme): ...
