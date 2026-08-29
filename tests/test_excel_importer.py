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
    assert len(corrected[0]["_errors"]) == 0
