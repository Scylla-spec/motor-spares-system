import os
import pytest
from utils.excel_importer import parse_excel_file, auto_correct_rows, import_parts_from_rows


def test_excel_importer_king_smurk():
    file_path = os.path.join("reorder_exports", "KING SMURK.xlsx")
    assert os.path.exists(file_path), "KING SMURK.xlsx file missing"

    raw_rows, warnings = parse_excel_file(file_path)
    assert len(raw_rows) > 1800, f"Expected > 1800 rows, got {len(raw_rows)}"

    first_row = raw_rows[0]
    assert first_row["part_number"] == "AC3032"
    assert first_row["name"] == "ACC CABLE TOY AC3032"
    assert str(first_row["quantity_on_hand"]) == "3"

    corrected = auto_correct_rows(raw_rows[:10])
    assert len(corrected) == 10
    assert corrected[0]["quantity_on_hand"] == 3
    # Rows with selling_price <= 0 are now flagged as errors
    assert len(corrected[0]["_errors"]) == 1
    assert "Selling price must be greater than 0" in corrected[0]["_errors"][0]


def test_zero_selling_price_blocked(test_db):
    row = {
        "part_number": "TEST-001",
        "name": "Test Part",
        "category": "Engine",
        "brand": "Toyota",
        "cost_price": 10.0,
        "selling_price": 0.0,
        "quantity_on_hand": 5,
        "reorder_level": 2,
    }
    corrected = auto_correct_rows([row])
    assert len(corrected[0]["_errors"]) == 1
    assert "Selling price must be greater than 0" in corrected[0]["_errors"][0]

    # Verification: import_parts_from_rows skips rows with _errors / selling_price <= 0
    res = import_parts_from_rows(corrected)
    assert res["imported"] == 0
    assert res["skipped"] == 1
    assert len(res["errors"]) == 1
