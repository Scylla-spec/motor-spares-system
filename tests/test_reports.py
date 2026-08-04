"""Tests for managers/reports_manager.py (FR-06, FR-10, FR-11)."""

from datetime import date
from models.part import Part
from models.sale import SaleItem
from managers.inventory_manager import add_part, get_all_parts
from managers.sales_manager import process_sale
from managers.reports_manager import get_daily_sales_summary, get_low_stock_parts


def _make_part(**overrides):
    defaults = dict(
        part_id=None, part_number="OF-001", name="Oil Filter", category="Engine",
        brand="Toyota", compatible_vehicles="Hilux", quantity_on_hand=10,
        cost_price=5, selling_price=8, reorder_level=5, supplier_id=None,
    )
    defaults.update(overrides)
    return Part(**defaults)


def test_low_stock_report_flags_parts_at_or_below_reorder_level(test_db):
    add_part(_make_part(quantity_on_hand=3, reorder_level=5))
    add_part(_make_part(part_number="BR-002", name="Brake Pad", quantity_on_hand=20, reorder_level=5))

    low_stock = get_low_stock_parts()

    assert len(low_stock) == 1
    assert low_stock[0]["part_number"] == "OF-001"


def test_daily_sales_summary_reflects_real_sale(test_db, admin_user):
    add_part(_make_part(quantity_on_hand=10, selling_price=8))
    part = get_all_parts()[0]
    item = SaleItem(sale_item_id=None, sale_id=None, part_id=part.part_id,
                     quantity=2, unit_price=part.selling_price, part_name=part.name)
    process_sale([item], "Cash", admin_user.user_id, admin_user.username)

    summary = get_daily_sales_summary(date.today().isoformat())

    assert summary["transaction_count"] == 1
    assert summary["total_revenue"] == 16.0


def test_daily_sales_summary_zero_for_date_with_no_sales(test_db):
    summary = get_daily_sales_summary("2020-01-01")
    assert summary["transaction_count"] == 0
    assert summary["total_revenue"] == 0