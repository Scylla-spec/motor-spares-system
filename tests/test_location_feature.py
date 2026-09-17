"""
Tests for physical warehouse storage location tracking (Rack, Row, Column).
"""

import pytest
from models.part import Part
from models.user import User
from managers.inventory_manager import add_part, get_all_parts, update_part, search_parts
from ui.inventory_screen import AddEditPartDialog, InventoryScreen
import sqlite3


def test_db_has_location_column(test_db):
    """Verify Part table in SQLite contains the location column."""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(Part);")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()
    assert "location" in columns


def test_add_and_get_part_with_location(test_db):
    """Verify add_part persists location and get_all_parts retrieves it."""
    part = Part(
        part_id=None,
        part_number="LOC-001",
        name="Front Strut",
        category="Suspension",
        brand="Monroe",
        compatible_vehicles="Toyota Hilux",
        quantity_on_hand=5,
        cost_price=50.0,
        selling_price=80.0,
        reorder_level=2,
        location="R3-2-1"
    )
    assert add_part(part) is True
    
    parts = get_all_parts()
    saved = next(p for p in parts if p.part_number == "LOC-001")
    assert saved.location == "R3-2-1"


def test_add_part_without_location_is_none(test_db):
    """Verify location is optional and defaults to None."""
    part = Part(
        part_id=None,
        part_number="LOC-002",
        name="Rear Shock",
        category="Suspension",
        brand="KYB",
        compatible_vehicles="Ford Ranger",
        quantity_on_hand=4,
        cost_price=30.0,
        selling_price=50.0,
        reorder_level=1
    )
    assert add_part(part) is True
    
    parts = get_all_parts()
    saved = next(p for p in parts if p.part_number == "LOC-002")
    assert saved.location is None


def test_update_part_location(test_db, admin_user):
    """Verify update_part successfully updates the location."""
    part = Part(
        part_id=None,
        part_number="LOC-003",
        name="Clutch Kit",
        category="Drivetrain",
        brand="Exedy",
        compatible_vehicles="Isuzu D-Max",
        quantity_on_hand=3,
        cost_price=100.0,
        selling_price=150.0,
        reorder_level=1,
        location="R1-1-1"
    )
    assert add_part(part) is True
    saved = next(p for p in get_all_parts() if p.part_number == "LOC-003")
    
    # Update to a new rack and row
    saved.location = "R4-3-2"
    assert update_part(saved, admin_user.user_id) is True
    
    updated = next(p for p in get_all_parts() if p.part_number == "LOC-003")
    assert updated.location == "R4-3-2"


def test_search_parts_by_location(test_db):
    """Verify search_parts finds items by location code."""
    p1 = Part(
        part_id=None,
        part_number="LOC-004",
        name="Brake Disc",
        category="Brakes",
        brand="Ferodo",
        compatible_vehicles="Nissan Hardbody",
        quantity_on_hand=6,
        cost_price=20.0,
        selling_price=35.0,
        reorder_level=2,
        location="R5-4-1"
    )
    add_part(p1)

    results = search_parts("R5-4-1")
    assert len(results) >= 1
    assert any(p.part_number == "LOC-004" for p in results)

    # Search partial rack
    results_rack = search_parts("R5-4")
    assert any(p.part_number == "LOC-004" for p in results_rack)


def test_add_edit_part_dialog_location_picker(qapp, admin_user):
    """Verify AddEditPartDialog rack/row/col dropdowns auto-populate location code."""
    dialog = AddEditPartDialog(current_user=admin_user)
    
    # Initially empty
    assert dialog.location_input.text() == ""
    
    # Select Rack 3
    idx_r = dialog.rack_combo.findData("3")
    dialog.rack_combo.setCurrentIndex(idx_r)
    # Default row and col are 1 when unspecified
    assert dialog.location_input.text() == "R3-1-1"
    
    # Select Row 2
    idx_rw = dialog.row_combo.findData("2")
    dialog.row_combo.setCurrentIndex(idx_rw)
    assert dialog.location_input.text() == "R3-2-1"
    
    # Select Col 2
    idx_c = dialog.col_combo.findData("2")
    dialog.col_combo.setCurrentIndex(idx_c)
    assert dialog.location_input.text() == "R3-2-2"


def test_add_edit_part_dialog_loads_existing_location(qapp, admin_user):
    """Verify Edit dialog parses R{rack}-{row}-{col} back into dropdowns."""
    part = Part(
        part_id=1,
        part_number="LOC-005",
        name="Spark Plug",
        category="Ignition",
        brand="NGK",
        compatible_vehicles="Honda Fit",
        quantity_on_hand=20,
        cost_price=2.0,
        selling_price=5.0,
        reorder_level=5,
        location="R6-3-2"
    )
    dialog = AddEditPartDialog(part=part, current_user=admin_user)
    
    assert dialog.location_input.text() == "R6-3-2"
    assert dialog.rack_combo.currentData() == "6"
    assert dialog.row_combo.currentData() == "3"
    assert dialog.col_combo.currentData() == "2"


def test_inventory_screen_table_and_filtering(qapp, test_db, admin_user, monkeypatch):
    """Verify InventoryScreen table has Location column and filters correctly."""
    dummy_parts = [
        Part(
            part_id=1,
            part_number="LOC-101",
            name="Air Filter A",
            category="Filters",
            brand="GUD",
            compatible_vehicles="Toyota",
            quantity_on_hand=10,
            cost_price=5.0,
            selling_price=10.0,
            reorder_level=2,
            location="R2-1-1"
        ),
        Part(
            part_id=2,
            part_number="LOC-102",
            name="Air Filter B",
            category="Filters",
            brand="GUD",
            compatible_vehicles="Toyota",
            quantity_on_hand=10,
            cost_price=5.0,
            selling_price=10.0,
            reorder_level=2,
            location="R7-3-2"
        ),
        Part(
            part_id=3,
            part_number="LOC-103",
            name="Fuel Filter C",
            category="Filters",
            brand="Bosch",
            compatible_vehicles="Isuzu",
            quantity_on_hand=5,
            cost_price=8.0,
            selling_price=15.0,
            reorder_level=2,
            location=None
        ),
    ]

    import ui.inventory_screen as inv_mod
    monkeypatch.setattr(inv_mod, "get_all_parts", lambda include_inactive=False: dummy_parts)

    screen = InventoryScreen(current_user=admin_user)
    screen.load_inventory()

    # Verify table column count and header
    assert screen.table.columnCount() == 9
    headers = [screen.table.horizontalHeaderItem(i).text() for i in range(9)]
    assert "Location" in headers
    loc_col = headers.index("Location")
    assert loc_col == 5

    # Verify all 3 parts loaded initially
    assert len(screen.filtered_parts) == 3

    # Test filtering by Rack 2
    r2_idx = screen.location_filter.findData("R2")
    assert r2_idx >= 0
    screen.location_filter.setCurrentIndex(r2_idx)
    assert len(screen.filtered_parts) == 1
    assert screen.filtered_parts[0].part_number == "LOC-101"

    # Test filtering by Unassigned
    unassigned_idx = screen.location_filter.findData("__UNASSIGNED__")
    assert unassigned_idx >= 0
    screen.location_filter.setCurrentIndex(unassigned_idx)
    assert len(screen.filtered_parts) == 1
    assert screen.filtered_parts[0].part_number == "LOC-103"

    # Reset location filter to All Locations
    all_idx = screen.location_filter.findData(None)
    screen.location_filter.setCurrentIndex(all_idx)
    assert len(screen.filtered_parts) == 3

    # Test search box filtering by location
    screen.search_input.setText("R7-3-2")
    assert len(screen.filtered_parts) == 1
    assert screen.filtered_parts[0].part_number == "LOC-102"

    screen.close()
