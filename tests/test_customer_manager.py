"""Tests for managers/customer_manager.py (FR-08)."""

from models.customer import Customer
from managers.customer_manager import add_customer, update_customer, get_all_customers


def test_add_and_retrieve_customer(test_db):
    add_customer(Customer(customer_id=None, name="T. Moyo", phone="0771112222", credit_balance=0))
    customers = get_all_customers()
    assert len(customers) == 1
    assert customers[0].name == "T. Moyo"


def test_customer_phone_is_optional(test_db):
    add_customer(Customer(customer_id=None, name="Walk-in Regular", phone="", credit_balance=0))
    customers = get_all_customers()
    assert len(customers) == 1


def test_update_customer_credit_balance(test_db):
    add_customer(Customer(customer_id=None, name="T. Moyo", phone="0771112222", credit_balance=0))
    customer = get_all_customers()[0]

    customer.credit_balance = 25.0
    update_customer(customer)

    assert get_all_customers()[0].credit_balance == 25.0