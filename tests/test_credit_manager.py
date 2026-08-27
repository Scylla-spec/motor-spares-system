"""
Tests for managers/credit_manager.py (Pay Later / On Credit feature).
"""
import pytest
from models.part import Part
from managers.inventory_manager import add_part, get_all_parts
from managers.credit_manager import (
    create_credit_order, get_credit_orders, get_credit_order_items,
    mark_credit_order_paid, get_credit_summary
)


def _make_part(**overrides):
    defaults = dict(
        part_id=None, part_number="BRK-001", name="Brake Pads", category="Brakes",
        brand="Ferodo", compatible_vehicles="Corolla", quantity_on_hand=15,
        cost_price=12, selling_price=20, reorder_level=3, supplier_id=None,
    )
    defaults.update(overrides)
    return Part(**defaults)


def test_create_credit_order_success(test_db, admin_user):
    add_part(_make_part(quantity_on_hand=10, selling_price=25.0))
    part = get_all_parts()[0]

    items = [{
        "part_id": part.part_id,
        "part_number": part.part_number,
        "part_name": part.name,
        "quantity": 4,
        "unit_price": part.selling_price
    }]

    ok, msg, credit_id = create_credit_order(
        customer_name="John Doe",
        items=items,
        cashier_id=admin_user.user_id,
        customer_phone="+26377111222",
        due_date="2026-08-30",
        notes="Promised to pay Friday"
    )

    assert ok is True
    assert credit_id is not None
    # Stock must be deducted from 10 to 6
    assert get_all_parts()[0].quantity_on_hand == 6

    # Verify orders
    orders = get_credit_orders(status_filter="Pending")
    assert len(orders) == 1
    assert orders[0].customer_name == "John Doe"
    assert orders[0].total_amount == 100.0
    assert orders[0].status == "Pending"

    # Verify items
    order_items = get_credit_order_items(credit_id)
    assert len(order_items) == 1
    assert order_items[0].quantity == 4
    assert order_items[0].part_name == "BRAKE PADS"


def test_create_credit_order_insufficient_stock(test_db, admin_user):
    add_part(_make_part(quantity_on_hand=3))
    part = get_all_parts()[0]

    items = [{
        "part_id": part.part_id,
        "part_number": part.part_number,
        "part_name": part.name,
        "quantity": 5,
        "unit_price": part.selling_price
    }]

    ok, msg, credit_id = create_credit_order(
        customer_name="Jane Smith",
        items=items,
        cashier_id=admin_user.user_id
    )

    assert ok is False
    assert "insufficient" in msg.lower()
    assert get_all_parts()[0].quantity_on_hand == 3


def test_mark_credit_order_paid(test_db, admin_user):
    add_part(_make_part(quantity_on_hand=10, selling_price=15.0))
    part = get_all_parts()[0]

    items = [{
        "part_id": part.part_id,
        "part_number": part.part_number,
        "part_name": part.name,
        "quantity": 2,
        "unit_price": 15.0
    }]

    ok, msg, credit_id = create_credit_order(
        customer_name="Alex Brown",
        items=items,
        cashier_id=admin_user.user_id
    )
    assert ok is True

    summary_before = get_credit_summary()
    assert summary_before["pending_count"] == 1
    assert summary_before["total_outstanding"] == 30.0

    # Mark as paid
    ok_pay, pay_msg = mark_credit_order_paid(credit_id, payment_method="EcoCash", cashier_id=admin_user.user_id)
    assert ok_pay is True

    # Pending list should now be empty
    pending = get_credit_orders(status_filter="Pending")
    assert len(pending) == 0

    # Paid list should contain this order
    paid_orders = get_credit_orders(status_filter="Paid")
    assert len(paid_orders) == 1
    assert paid_orders[0].status == "Paid"
    assert paid_orders[0].amount_paid == 30.0

    summary_after = get_credit_summary()
    assert summary_after["pending_count"] == 0
    assert summary_after["paid_count"] == 1
    assert summary_after["total_paid"] == 30.0
