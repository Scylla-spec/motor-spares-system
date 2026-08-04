"""Tests for managers/supplier_manager.py (FR-09)."""

from models.supplier import Supplier
from managers.supplier_manager import add_supplier, get_all_suppliers


def test_add_and_retrieve_supplier(test_db):
    add_supplier(Supplier(supplier_id=None, name="Solatek", contact_phone="0718188890", address=""))
    suppliers = get_all_suppliers()
    assert len(suppliers) == 1
    assert suppliers[0].name == "Solatek"