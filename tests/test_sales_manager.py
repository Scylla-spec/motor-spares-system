"""
Tests for managers/sales_manager.py: FR-04 (sale + auto stock deduction),
BR-01 (stock can't go negative -- a sale must not oversell).
"""

from models.part import Part
from models.sale import SaleItem
from managers.inventory_manager import add_part, get_all_parts
from managers.sales_manager import process_sale


def _make_part(**overrides):
    defaults = dict(
        part_id=None, part_number="OF-001", name="Oil Filter", category="Engine",
        brand="Toyota", compatible_vehicles="Hilux", quantity_on_hand=10,
        cost_price=5, selling_price=8, reorder_level=2, supplier_id=None,
    )
    defaults.update(overrides)
    return Part(**defaults)


def test_successful_sale_deducts_stock(test_db, admin_user):
    add_part(_make_part(quantity_on_hand=10))
    part = get_all_parts()[0]

    item = SaleItem(sale_item_id=None, sale_id=None, part_id=part.part_id,
                     quantity=3, unit_price=part.selling_price, part_name=part.name)

    ok, result = process_sale([item], "Cash", admin_user.user_id, admin_user.username)

    assert ok is True
    assert get_all_parts()[0].quantity_on_hand == 7


def test_sale_blocked_when_insufficient_stock(test_db, admin_user):
    """TC-01 from the documentation: selling more than available stock must be blocked."""
    add_part(_make_part(quantity_on_hand=5))
    part = get_all_parts()[0]

    item = SaleItem(sale_item_id=None, sale_id=None, part_id=part.part_id,
                     quantity=10, unit_price=part.selling_price, part_name=part.name)

    ok, result = process_sale([item], "Cash", admin_user.user_id, admin_user.username)

    assert ok is False
    assert "insufficient" in result.lower()
    assert get_all_parts()[0].quantity_on_hand == 5


def test_empty_cart_is_rejected(test_db, admin_user):
    ok, result = process_sale([], "Cash", admin_user.user_id, admin_user.username)
    assert ok is False
    assert "empty" in result.lower()


def test_sale_records_correct_total(test_db, admin_user):
    add_part(_make_part(quantity_on_hand=10, selling_price=8.50))
    part = get_all_parts()[0]

    item = SaleItem(sale_item_id=None, sale_id=None, part_id=part.part_id,
                     quantity=2, unit_price=part.selling_price, part_name=part.name)

    ok, result = process_sale([item], "Cash", admin_user.user_id, admin_user.username)
    assert ok is True

    from database.db_manager import get_connection
    conn = get_connection()
    row = conn.execute("SELECT total_amount FROM Sale ORDER BY sale_id DESC LIMIT 1").fetchone()
    conn.close()
    assert row["total_amount"] == 17.00