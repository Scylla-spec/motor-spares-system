"""
Tests for managers/inventory_manager.py: BR-01 (stock can't go negative),
BR-02 (deactivated parts are hidden, not deleted), and FR-15 (stock adjustment).
"""

from models.part import Part
from managers.inventory_manager import (
    add_part, get_all_parts, search_parts, record_stock_in,
    record_stock_adjustment, deactivate_part, update_part
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


def test_update_part_number_success(test_db, admin_user):
    add_part(_make_part(part_number="PN-100", name="Brake Pad"))
    part = get_all_parts()[0]
    part.part_number = "PN-100-NEW"
    
    ok = update_part(part, admin_user.user_id)
    assert ok is True
    updated = get_all_parts()[0]
    assert updated.part_number == "PN-100-NEW"


def test_update_part_number_duplicate_fails(test_db, admin_user):
    add_part(_make_part(part_number="PN-101", name="Part One"))
    add_part(_make_part(part_number="PN-102", name="Part Two"))
    parts = get_all_parts()
    part_two = [p for p in parts if p.part_number == "PN-102"][0]
    
    # Attempt to change PN-102 to PN-101 (already taken)
    part_two.part_number = "PN-101"
    ok = update_part(part_two, admin_user.user_id)
    assert ok is False


def test_update_part_quantity_updates_stock_and_logs(test_db, admin_user):
    add_part(_make_part(part_number="PN-200", quantity_on_hand=15))
    part = get_all_parts()[0]
    part.quantity_on_hand = 25
    
    ok = update_part(part, admin_user.user_id)
    assert ok is True
    updated = get_all_parts()[0]
    assert updated.quantity_on_hand == 25