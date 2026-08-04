import pytest
from datetime import datetime
from database.db_manager import get_connection
from utils.numbering import generate_customer_code, generate_receipt_number, generate_po_number


def test_customer_code_formatting():
    assert generate_customer_code(1) == "CUS-00001"
    assert generate_customer_code(102) == "CUS-00102"
    assert generate_customer_code(99999) == "CUS-99999"
    assert generate_customer_code(None) == ""


def test_receipt_number_format(test_db):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime(2026, 8, 4)
    rec_no = generate_receipt_number(cursor, today)
    assert rec_no.startswith("REC-20260804-")
    conn.close()


def test_po_number_format(test_db):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime(2026, 8, 4)
    po_no = generate_po_number(cursor, today)
    assert po_no.startswith("PO-20260804-")
    conn.close()
