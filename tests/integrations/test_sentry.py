from copy import copy
from types import SimpleNamespace

import pytest

import comfort.integrations.sentry
import frappe
from comfort.integrations.sentry import _get_user_email, _GetSentryInfoPayload, get_info


def test_sentry_get_info(monkeypatch: pytest.MonkeyPatch):
    exp_dsn = "test_dsn"
    exp_version = ("1.53.7",)
    exp_release = f"comfort@{exp_version}"
    monkeypatch.setenv("SENTRY_DSN", exp_dsn)

    def mock_distribution(distribution_name: str):
        return SimpleNamespace(metadata={"Version": exp_version})

    monkeypatch.setattr(comfort.integrations.sentry, "distribution", mock_distribution)
    assert get_info() == _GetSentryInfoPayload(dsn=exp_dsn, release=exp_release)


def test_get_user_email_no_session():
    prev_session = copy(frappe.session)
    frappe.session = None
    assert _get_user_email() is None
    frappe.session = prev_session  # Cleanup for other tests


def test_get_user_email_no_session_user():
    prev_session = copy(frappe.session)
    frappe.session.user = None
    assert _get_user_email() is None
    frappe.session = prev_session


def test_get_user_email_executed():
    user, exp_email = "Administrator", "test@email.com"
    frappe.db.set_value("User", user, "email", exp_email)
    prev_session = copy(frappe.session)
    frappe.session = SimpleNamespace(user=user)
    assert _get_user_email() == exp_email
    frappe.session = prev_session
