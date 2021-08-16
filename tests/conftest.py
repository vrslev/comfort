from unittest.mock import MagicMock

import pytest
from pymysql import OperationalError

import frappe

TEST_SITE_NAME = "tests"


@pytest.fixture
def db_instance():
    """Init frappe, connect to database, do nothing on db.commit()"""
    frappe.init(site=TEST_SITE_NAME, sites_path="../../sites")
    frappe.connect()
    frappe.db.commit = MagicMock()
    yield frappe.db
    frappe.destroy()


@pytest.fixture(autouse=True)
def db_transaction(db_instance: frappe.MariaDBDatabase):
    """Rollback after db transaction"""
    try:
        db_instance.begin()
    except OperationalError as e:
        pytest.exit(str(e), returncode=1)

    yield db_instance
    db_instance.rollback()
