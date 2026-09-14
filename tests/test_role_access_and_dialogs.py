"""
Tests for role-based access control and AddEditPartDialog behavior:
1. Edit Part allows Admin to edit Part# and blocks Cashier.
2. Edit Part allows setting/updating Initial Quantity.
3. Cashier dashboard hides Reports nav item; Admin dashboard includes Reports.
4. Cashier accessing ReportsScreen directly sees Access Denied.
5. InventoryScreen preserve_page pagination behavior.
"""

import pytest
from models.part import Part
from ui.inventory_screen import AddEditPartDialog, InventoryScreen
from ui.reports_screen import ReportsScreen
from ui.dashboard import DashboardWindow


def _sample_part():
    return Part(
        part_id=1,
        part_number="BRK-001",
        name="Front Brake Pads",
        category="Brakes",
        brand="Brembo",
        compatible_vehicles="Toyota Hilux",
        quantity_on_hand=10,
        cost_price=25.0,
        selling_price=40.0,
        reorder_level=5,
        supplier_id=None
    )


def test_edit_part_dialog_admin_can_edit_part_number_and_qty(qapp, admin_user):
    part = _sample_part()
    dialog = AddEditPartDialog(part=part, current_user=admin_user)
    
    # Admin should be able to edit Part#
    assert dialog.part_number.isEnabled() is True
    assert dialog.part_number.text() == "BRK-001"
    
    # Quantity on hand field should be enabled and populated
    assert dialog.quantity_on_hand.isEnabled() is True
    assert dialog.quantity_on_hand.value() == 10


def test_edit_part_dialog_cashier_cannot_edit_part_number(qapp, cashier_user):
    part = _sample_part()
    dialog = AddEditPartDialog(part=part, current_user=cashier_user)
    
    # Cashier cannot edit Part#
    assert dialog.part_number.isEnabled() is False
    assert "Admin access required" in dialog.part_number.toolTip()
    
    # But quantity should still be enabled
    assert dialog.quantity_on_hand.isEnabled() is True


def test_dashboard_hides_reports_for_cashier(qapp, test_db, cashier_user):
    dash = DashboardWindow(current_user=cashier_user)
    
    # Collect all sidebar labels
    labels = [dash.sidebar_list.item(i).text() for i in range(dash.sidebar_list.count())]
    
    assert "Reports" not in labels
    assert "User Management" not in labels
    assert "Settings" not in labels
    assert "Inventory" in labels
    assert "Point of Sale" in labels
    dash.close()


def test_dashboard_shows_reports_for_admin(qapp, test_db, admin_user):
    dash = DashboardWindow(current_user=admin_user)
    labels = [dash.sidebar_list.item(i).text() for i in range(dash.sidebar_list.count())]
    
    assert "Reports" in labels
    assert "User Management" in labels
    assert "Settings" in labels
    dash.close()


def test_reports_screen_access_denied_for_cashier(qapp, cashier_user):
    screen = ReportsScreen(current_user=cashier_user)
    # Finding any labels with Access Denied
    text_content = screen.findChildren(object)
    denied = any("Access Denied" in str(getattr(c, 'text', lambda: '')()) for c in text_content)
    assert denied is True


def test_inventory_screen_preserves_page_on_reload(qapp, test_db, admin_user, monkeypatch):
    import ui.inventory_screen as inv_screen
    # Create 150 dummy parts so we have multiple pages
    dummy_parts = [
        Part(
            part_id=i,
            part_number=f"SKU-{i:04d}",
            name=f"Part {i}",
            category="Engine",
            brand="OEM",
            compatible_vehicles="All",
            quantity_on_hand=5,
            cost_price=10.0,
            selling_price=15.0,
            reorder_level=2,
            supplier_id=None
        )
        for i in range(1, 151)
    ]
    monkeypatch.setattr(inv_screen, "get_all_parts", lambda include_inactive=False: dummy_parts)
    
    screen = InventoryScreen(current_user=admin_user)
    screen.PAGE_SIZE = 50
    screen.load_inventory()
    
    # Navigate to page 2
    screen.next_page()
    assert screen.current_page == 2
    
    # Reload inventory with preserve_page=True
    screen.load_inventory(preserve_page=True)
    assert screen.current_page == 2
    
    # Reload inventory without preserve_page (e.g. initial load or filter change)
    screen.load_inventory(preserve_page=False)
    assert screen.current_page == 1
    screen.close()
