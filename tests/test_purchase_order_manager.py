import os
import pytest
from managers.supplier_manager import add_supplier, get_all_suppliers
from managers.inventory_manager import add_part, get_all_parts
from managers.purchase_order_manager import (
    create_po_with_items, get_po_items, get_po_by_id,
    receive_po_stock, get_all_pos, get_low_stock_parts_for_reorder
)
from models.supplier import Supplier
from models.part import Part
from utils.po_export import generate_po_pdf
from database.db_manager import get_connection


@pytest.fixture
def sample_supplier(test_db):
    s = Supplier(supplier_id=None, name="Bosch Auto Parts", contact_phone="12345678", address="123 Industrial Rd")
    add_supplier(s)
    suppliers = get_all_suppliers()
    return suppliers[0]


@pytest.fixture
def sample_parts(test_db):
    p1 = Part(
        part_id=None, part_number="BP-001", name="Brake Pad Set", category="Braking",
        brand="Brembo", compatible_vehicles="Toyota Hilux", quantity_on_hand=4,
        cost_price=20.0, selling_price=35.0, reorder_level=10
    )
    p2 = Part(
        part_id=None, part_number="OF-002", name="Oil Filter", category="Filters",
        brand="Bosch", compatible_vehicles="Universal", quantity_on_hand=2,
        cost_price=5.0, selling_price=10.0, reorder_level=5
    )
    add_part(p1)
    add_part(p2)
    parts = get_all_parts()
    return parts


def test_create_po_with_items(sample_supplier, sample_parts):
    items = [
        {"part_id": sample_parts[0].part_id, "part_number": sample_parts[0].part_number, "part_name": sample_parts[0].name, "quantity_ordered": 10, "unit_cost": 18.0},
        {"part_id": sample_parts[1].part_id, "part_number": sample_parts[1].part_number, "part_name": sample_parts[1].name, "quantity_ordered": 20, "unit_cost": 4.50},
    ]
    ok, po_num, po_id = create_po_with_items(sample_supplier.supplier_id, items, status="Ordered")
    assert ok is True
    assert po_id is not None
    assert po_num.startswith("PO-")

    po = get_po_by_id(po_id)
    assert po is not None
    assert po.supplier_id == sample_supplier.supplier_id
    assert po.total_cost == (10 * 18.0) + (20 * 4.50)
    assert len(po.items) == 2
    assert po.items[0].part_number == "BP-001"
    assert po.items[0].quantity_ordered == 10


def test_receive_po_stock_updates_inventory(sample_supplier, sample_parts):
    part1 = sample_parts[0]
    initial_qty = part1.quantity_on_hand  # 4

    items = [
        {"part_id": part1.part_id, "part_number": part1.part_number, "part_name": part1.name, "quantity_ordered": 15, "unit_cost": 18.0}
    ]
    ok, po_num, po_id = create_po_with_items(sample_supplier.supplier_id, items, status="Ordered")
    assert ok is True

    # Receive stock
    rec_ok, rec_msg = receive_po_stock(po_id)
    assert rec_ok is True

    # Verify inventory was incremented
    updated_parts = get_all_parts()
    updated_p1 = next(p for p in updated_parts if p.part_id == part1.part_id)
    assert updated_p1.quantity_on_hand == initial_qty + 15

    # Verify PO status is 'Received'
    po = get_po_by_id(po_id)
    assert po.status == "Received"

    # Verify stock movement record created
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM StockMovement WHERE part_id = ? AND movement_type = 'IN'", (part1.part_id,))
    movements = cursor.fetchall()
    conn.close()
    assert len(movements) >= 1
    assert movements[-1]["quantity"] == 15


def test_receive_po_stock_prevents_duplicate(sample_supplier, sample_parts):
    items = [
        {"part_id": sample_parts[0].part_id, "part_number": sample_parts[0].part_number, "part_name": sample_parts[0].name, "quantity_ordered": 5, "unit_cost": 20.0}
    ]
    ok, po_num, po_id = create_po_with_items(sample_supplier.supplier_id, items)
    assert ok is True

    # First receive succeeds
    ok1, _ = receive_po_stock(po_id)
    assert ok1 is True

    # Second receive fails
    ok2, msg = receive_po_stock(po_id)
    assert ok2 is False
    assert "already been received" in msg.lower()


def test_get_low_stock_parts_for_reorder(sample_parts):
    low_stock = get_low_stock_parts_for_reorder()
    assert len(low_stock) >= 2
    part_numbers = [p["part_number"] for p in low_stock]
    assert "BP-001" in part_numbers
    assert "OF-002" in part_numbers


def test_generate_po_pdf(sample_supplier, sample_parts):
    items = [
        {"part_id": sample_parts[0].part_id, "part_number": sample_parts[0].part_number, "part_name": sample_parts[0].name, "quantity_ordered": 10, "unit_cost": 20.0}
    ]
    ok, po_num, po_id = create_po_with_items(sample_supplier.supplier_id, items)
    po = get_po_by_id(po_id)

    pdf_path = generate_po_pdf(po)
    assert pdf_path != ""
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 0
