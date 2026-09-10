"""
Tests for managers/inventory_manager.py: BR-01 (stock can't go negative),
BR-02 (deactivated parts are hidden, not deleted), and FR-15 (stock adjustment).
"""

from models.part import Part
from managers.inventory_manager import (
    add_part, get_all_parts, search_parts, record_stock_in,
    record_stock_adjustment, deactivate_part
)


def _make_part(**overrides):
    defaults = dict(
        part_id=None, part_number="OF-001", name="Oil Filter", category="Engine",
        brand="Toyota", compatible_vehicles="Hilux", quantity_on_hand=10,
        cost_price=5, selling_price=8, reorder_level=2, supplier_id=None,
    )
    defaults.update(overrides)
    return Part(**defaults)


def test_add_part_and_retrieve(test_db):
    add_part(_make_part())
    parts = get_all_parts()
    assert len(parts) == 1
    assert parts[0].part_number == "OF-001"


def test_stock_adjustment_blocks_negative_stock(test_db, admin_user):
    add_part(_make_part(quantity_on_hand=5))
    part_id = get_all_parts()[0].part_id

    ok, msg = record_stock_adjustment(part_id, -100, "Test overshoot", admin_user.user_id)

    assert ok is False
    assert "negative" in msg.lower()
    assert get_all_parts()[0].quantity_on_hand == 5


def test_stock_adjustment_requires_a_reason(test_db, admin_user):
    add_part(_make_part())
    part_id = get_all_parts()[0].part_id

    ok, msg = record_stock_adjustment(part_id, 5, "", admin_user.user_id)

    assert ok is False
    assert "reason" in msg.lower()


def test_stock_adjustment_applies_correctly(test_db, admin_user):
    add_part(_make_part(quantity_on_hand=10))
    part_id = get_all_parts()[0].part_id

    ok, msg = record_stock_adjustment(part_id, -3, "Damaged in storage", admin_user.user_id)
    assert ok is True
    assert get_all_parts()[0].quantity_on_hand == 7

    ok, msg = record_stock_adjustment(part_id, 5, "Found extra stock", admin_user.user_id)
    assert ok is True
    assert get_all_parts()[0].quantity_on_hand == 12


def test_deactivated_part_hidden_from_default_search(test_db, admin_user):
    add_part(_make_part())
    part_id = get_all_parts()[0].part_id

    deactivate_part(part_id, user_id=admin_user.user_id)

    assert get_all_parts() == []
    assert search_parts("Oil") == []
    assert len(get_all_parts(include_inactive=True)) == 1


def test_record_stock_in_increases_quantity(test_db):
    add_part(_make_part(quantity_on_hand=10))
    part_id = get_all_parts()[0].part_id

    record_stock_in(part_id, 20)

    assert get_all_parts()[0].quantity_on_hand == 30


def test_part_vehicle_type_persistence(test_db):
    add_part(_make_part(part_number="BK-001", name="Chain Kit", vehicle_type="Motorbike"))
    add_part(_make_part(part_number="CR-001", name="Brake Disk", vehicle_type="Car"))
    add_part(_make_part(part_number="BT-001", name="Universal Spark Plug", vehicle_type="Both"))

    parts = get_all_parts()
    assert len(parts) == 3
    vt_map = {p.part_number: p.vehicle_type for p in parts}
    assert vt_map["BK-001"] == "Motorbike"
    assert vt_map["CR-001"] == "Car"
    assert vt_map["BT-001"] == "Both"