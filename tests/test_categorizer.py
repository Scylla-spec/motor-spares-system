import pytest
from utils.categorizer import infer_category, categorize_existing_parts_in_db
from managers.inventory_manager import get_all_parts


def test_infer_category():
    assert infer_category("ACC CABLE TOY AC3032") == "CABLES & CONTROLS"
    assert infer_category("AIR CLEANER HOSE Y-SER RH7001") == "COOLING & HEATING"
    assert infer_category("SPARK PLUG BP5ES") == "SPARK PLUGS & IGNITION"
    assert infer_category("OIL FILTER N3012") == "FILTERS"
    assert infer_category("BEARING 30209") == "BEARINGS & SEALS"
    assert infer_category("BRAKE PAD SET FRONT") == "BRAKE SYSTEM"
    assert infer_category("FAN BELT 4PK850") == "BELTS & PULLEYS"
    assert infer_category("UNKNOWN XYZ PART") == "GENERAL SPARES"


def test_categorize_existing_parts_in_db():
    parts = get_all_parts()
    categorized = [p for p in parts if p.category]
    assert len(categorized) > 0, "Expected database parts to have populated categories"
