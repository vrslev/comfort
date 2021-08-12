from unittest.mock import MagicMock

import pytest

import frappe
from frappe.defaults import *


@pytest.fixture(scope="session")
def db_instance():
    """Init frappe, connect to database, do nothing on db.commit()"""
    frappe.init(site="tests", sites_path="../../sites")
    frappe.connect()
    frappe.db.commit = MagicMock()
    yield frappe.db


@pytest.fixture(autouse=True)
def db_transaction(db_instance: frappe.db):
    """Rollback on db transaction"""
    db_instance.begin()
    yield db_instance
    db_instance.rollback()
