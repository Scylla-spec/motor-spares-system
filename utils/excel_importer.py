"""
Excel Bulk Import Utility
=========================
Reads .xlsx files, auto-corrects common formatting/spelling errors,
and imports parts into the inventory.

All columns are optional — any column the importer recognises is
mapped automatically; any that are missing simply stay blank and are
shown in the review table for the user to fill in before committing.
Part Number is auto-generated (IMP-NNNNN) when absent so no row is
silently lost before the user even sees it.
"""
import re
import logging
from typing import List, Dict, Any, Tuple
import openpyxl
from thefuzz import process as fuzz_process

from database.db_manager import get_connection
from managers.inventory_manager import add_part, get_all_parts
from managers.supplier_manager import get_all_suppliers
from models.part import Part

# ---------------------------------------------------------------------------
# Column name aliases — maps any variant to a canonical field name
# ---------------------------------------------------------------------------
COLUMN_ALIASES = {
    "part_number":         ["part number", "part no", "part no.", "partno", "part_no",
                             "code", "item code", "sku", "stock code", "part#", "partcode", "itemcode"],
    "name":                ["name", "description", "part name", "item name", "item description",
                             "product name", "part description",
                             "stocks", "stock", "stock name", "item", "desc", "stock description"],
    "category":            ["category", "cat", "type", "group", "product type", "dept", "department"],
    "brand":               ["brand", "manufacturer", "make", "mfr", "mfg"],
    "compatible_vehicles": ["compatible vehicles", "vehicles", "fits", "vehicle",
                             "compatibility", "application", "for vehicle"],
    "cost_price":          ["cost price", "cost", "buy price", "purchase price", "unit cost",
                             "buying price", "net price", "cost_price"],
    "selling_price":       ["selling price", "sell price", "sale price", "retail price",
                             "price", "unit price", "rrp", "selling_price"],
    "quantity_on_hand":    ["quantity", "qty", "quantity on hand", "on hand",
                             "stock qty", "stock quantity", "units",
                             "stock available", "available", "available stock", "balance",
                             "onhand", "on_hand"],
    "reorder_level":       ["reorder level", "reorder", "min stock", "minimum stock",
                             "reorder point", "min qty", "reorder_level"],
    "supplier":            ["supplier", "vendor", "supplier name"],
}

# Counter used to generate unique placeholder part numbers within a single
# import session.  Reset each time auto_correct_rows() is called.
_placeholder_counter = 0


def _next_placeholder() -> str:
    """Returns the next IMP-NNNNN placeholder part number."""
    global _placeholder_counter
    _placeholder_counter += 1
    return f"IMP-{_placeholder_counter:05d}"


def _normalise(text: str) -> str:
    """Lowercase, strip whitespace for comparison."""
    return str(text).lower().strip()


def _normalize_row_cells(row: tuple) -> List[str]:
    """
    Normalizes a tuple of cell values.
    If a cell contains tab characters (\t), splits them so tab-separated cell
    contents are properly separated into columns.
    Returns a list of raw string values (or empty strings for None).
    """
    result = []
    for cell in row:
        if cell is None:
            result.append("")
        else:
            val_str = str(cell)
            if "\t" in val_str:
                parts = val_str.split("\t")
                result.extend([p.strip() for p in parts])
            else:
                result.append(val_str.strip())
    return result


def _score_header_row(cells: List[str]) -> Tuple[Dict[str, int], int]:
    """
    Evaluates a list of header cell strings.
    Returns (col_map, score) where score is the number of distinct canonical fields matched.
    """
    mapping = {}
    normalised = [_normalise(c) for c in cells]
    for field, aliases in COLUMN_ALIASES.items():
        for idx, h in enumerate(normalised):
            if h in aliases and field not in mapping:
                mapping[field] = idx
                break
    return mapping, len(mapping)


def parse_excel_file(filepath: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses an Excel file and returns:
    - list of raw row dicts with canonical field names
    - list of informational warnings (never hard errors here)

    Automatically scans worksheets and header candidate rows to pick the best-matching
    header layout. Supports tab-delimited strings within cells and sparse tables.
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)
    if not wb.sheetnames:
        return [], ["The spreadsheet appears to be empty."]

    best_rows = []
    best_col_map = {}
    best_header_row_idx = -1
    best_max_score = 0

    warnings = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        raw_rows = list(ws.iter_rows(values_only=True))
        if not raw_rows:
            continue

        sheet_best_score = 0
        sheet_best_map = {}
        sheet_best_row_idx = -1

        non_empty_count = 0
        for i, raw_row in enumerate(raw_rows):
            if all(cell is None for cell in raw_row):
                continue
            non_empty_count += 1
            if non_empty_count > 25:
                break

            cells = _normalize_row_cells(raw_row)
            col_map, score = _score_header_row(cells)
            if score > sheet_best_score:
                sheet_best_score = score
                sheet_best_map = col_map
                sheet_best_row_idx = i

        if sheet_best_score > best_max_score:
            best_max_score = sheet_best_score
            best_col_map = sheet_best_map
            best_header_row_idx = sheet_best_row_idx
            best_rows = raw_rows

    if not best_rows:
        return [], ["The spreadsheet appears to be empty."]

    # If no headers matched across any sheet, fall back to active worksheet
    if best_max_score == 0:
        ws = wb.active
        best_rows = list(ws.iter_rows(values_only=True))
        best_header_row_idx = 0
        for i, row in enumerate(best_rows):
            if any(cell is not None for cell in row):
                best_header_row_idx = i
                break

    if best_max_score > 0:
        undetected = [f for f in ("part_number", "name") if f not in best_col_map]
        if undetected:
            readable = {"part_number": "Part Number", "name": "Name"}
            names = " and ".join(readable[f] for f in undetected)
            warnings.append(
                f"[INFO] {names} column(s) were not detected — auto-generated placeholders "
                f"will be used. Please fill in the correct values in the review table."
            )
    else:
        warnings.append(
            "[INFO] No column headers were recognised. Treating the data as a single "
            "column and placing everything in 'Name'. Please correct the values "
            "in the review table before importing."
        )

    parsed_rows = []
    if best_max_score == 0:
        for row in best_rows[best_header_row_idx + 1:]:
            if all(cell is None for cell in row):
                continue
            cells = _normalize_row_cells(row)
            non_empty = [c for c in cells if c]
            if non_empty:
                record = {"name": " | ".join(non_empty)}
                parsed_rows.append(record)
        return parsed_rows, warnings

    for row in best_rows[best_header_row_idx + 1:]:
        if all(cell is None for cell in row):
            continue
        cells = _normalize_row_cells(row)
        if not any(cells):
            continue

        record = {}
        for field, col_idx in best_col_map.items():
            record[field] = cells[col_idx] if col_idx < len(cells) and cells[col_idx] != "" else None

        if any(v is not None for v in record.values()):
            parsed_rows.append(record)

    return parsed_rows, warnings


def _clean_numeric(value: Any) -> float:
    """Strip currency symbols and commas, return float."""
    if value is None:
        return 0.0
    cleaned = re.sub(r"[^\d.\-]", "", str(value).strip().replace(",", "."))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def _clean_int(value: Any) -> int:
    """Clean and return integer."""
    return int(_clean_numeric(value))


def _fuzzy_correct(value: str, choices: List[str], threshold: int = 80) -> Tuple[str, bool]:
    """
    Fuzzy-match value against choices.
    Returns (corrected_value, was_corrected).
    """
    if not value or not choices:
        return value, False
    value_norm = value.strip()
    if value_norm in choices:
        return value_norm, False
    result = fuzz_process.extractOne(value_norm, choices)
    if result and result[1] >= threshold:
        corrected = result[0]
        return corrected, (corrected != value_norm)
    return value_norm, False


def auto_correct_rows(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Applies auto-correction to each row:
    - Cleans numeric fields
    - Fuzzy-corrects category/brand/supplier against existing DB values
    - Auto-generates placeholder part numbers when missing
    - Adds '_warnings' and '_corrections' keys per row
    - Only adds '_errors' for truly unrecoverable problems (negative price)
    """
    global _placeholder_counter
    _placeholder_counter = 0  # reset per import session

    # Pull existing values from DB for fuzzy matching
    parts = get_all_parts()
    existing_categories = list({p.category for p in parts if p.category})
    existing_brands = list({p.brand for p in parts if p.brand})
    suppliers = get_all_suppliers()
    supplier_map = {s.name: s.supplier_id for s in suppliers}
    supplier_names = list(supplier_map.keys())

    corrected_rows = []
    for row in raw_rows:
        warnings = []
        corrections = []
        clean = dict(row)

        # --- Part Number ---
        raw_pn = str(clean.get("part_number", "") or "").strip().upper()
        if not raw_pn:
            # Auto-generate a placeholder so the row survives to the review
            # table — the user can type the real number before importing.
            placeholder = _next_placeholder()
            clean["part_number"] = placeholder
            warnings.append(
                f"Part Number was missing — assigned placeholder '{placeholder}'. "
                "Please replace it with the correct part number before importing."
            )
        else:
            clean["part_number"] = raw_pn

        # --- Name ---
        name = str(clean.get("name", "") or "").strip()
        if name:
            name = name.strip().upper()
        else:
            warnings.append(
                "Name is missing — please fill it in before importing."
            )
        clean["name"] = name

        # --- Category: fuzzy correct or infer ---
        raw_cat = str(clean.get("category", "") or "").strip().upper()
        if raw_cat:
            fixed_cat, was_fixed = _fuzzy_correct(raw_cat, existing_categories)
            if was_fixed:
                corrections.append(f"Category: '{raw_cat}' → '{fixed_cat.upper()}'")
            clean["category"] = fixed_cat.upper()
        else:
            from utils.categorizer import infer_category
            clean["category"] = infer_category(clean["name"], clean["part_number"])

        # --- Brand: fuzzy correct ---
        raw_brand = str(clean.get("brand", "") or "").strip().upper()
        if raw_brand:
            fixed_brand, was_fixed = _fuzzy_correct(raw_brand, existing_brands)
            if was_fixed:
                corrections.append(f"Brand: '{raw_brand}' → '{fixed_brand.upper()}'")
            clean["brand"] = fixed_brand.upper()
        else:
            clean["brand"] = raw_brand

        # --- Compatible Vehicles ---
        clean["compatible_vehicles"] = str(clean.get("compatible_vehicles", "") or "").strip().upper()

        # --- Numeric fields ---
        clean["cost_price"] = _clean_numeric(clean.get("cost_price", 0))
        clean["selling_price"] = _clean_numeric(clean.get("selling_price", 0))
        clean["quantity_on_hand"] = _clean_int(clean.get("quantity_on_hand", 0))
        clean["reorder_level"] = _clean_int(clean.get("reorder_level", 5))

        # Selling price sanity check
        if clean["selling_price"] > 0 and clean["selling_price"] < clean["cost_price"]:
            warnings.append("Selling price is less than cost price — please review.")

        # --- Supplier: fuzzy correct then resolve to ID ---
        raw_supplier = str(clean.get("supplier", "") or "").strip()
        if raw_supplier and supplier_names:
            fixed_sup, was_fixed = _fuzzy_correct(raw_supplier, supplier_names)
            if was_fixed:
                corrections.append(f"Supplier: '{raw_supplier}' → '{fixed_sup}'")
            clean["supplier_id"] = supplier_map.get(fixed_sup)
        else:
            clean["supplier_id"] = None

        # --- Errors: only truly unrecoverable issues ---
        errors = []
        if clean.get("cost_price", 0) < 0:
            errors.append("Cost price cannot be negative.")

        clean["_warnings"] = warnings
        clean["_corrections"] = corrections
        clean["_errors"] = errors
        corrected_rows.append(clean)

    return corrected_rows

def _find_existing_part(part_number: str, name: str):
    """
    Looks for an existing active part that matches by part_number first,
    then by name (case-insensitive). Returns the Part object or None.
    Used by import_parts_from_rows to detect duplicates before inserting.
    """
    from managers.inventory_manager import search_parts
    pn = (part_number or "").strip().upper()
    nm = (name or "").strip().lower()

    if pn:
        results = search_parts(pn)
        for p in results:
            if p.part_number.upper() == pn:
                return p

    if nm:
        results = search_parts(nm)
        for p in results:
            if p.name.strip().lower() == nm:
                return p

    return None


def import_parts_from_rows(corrected: List[Dict[str, Any]], parse_warnings: List[str] = None) -> Dict[str, Any]:
    """
    Commits already-parsed-and-corrected rows to inventory. This is the
    shared tail end used by both Excel import and Image/OCR import (FR-19)
    — and critically, it's what lets a user's manual corrections in the
    review table actually get committed, instead of the import silently
    re-reading the original source file from scratch.

    Duplicate handling:
    - If an imported row matches an existing part (by part_number or name),
      the quantity from the import is added to the existing part's stock
      rather than inserting a duplicate. All other fields are left unchanged.
    - A row with no part_number AND no name is skipped entirely.
    """
    from managers.inventory_manager import record_stock_in

    imported = 0
    merged = 0
    skipped = 0
    all_warnings = list(parse_warnings or [])
    all_errors = []

    for i, row in enumerate(corrected, start=1):
        if row.get("_errors"):
            all_errors.append(f"Row {i} ({row.get('part_number','?')}): {'; '.join(row['_errors'])}")
            skipped += 1
            continue

        # A row is only skipped if both part_number AND name are still blank
        # after the user's review (i.e. they didn't fill anything in).
        if not row.get("part_number") and not row.get("name"):
            all_errors.append(f"Row {i}: Both Part Number and Name are empty — skipped.")
            skipped += 1
            continue

        # If only name is still blank, use a fallback so import doesn't silently fail
        if not row.get("name"):
            row["name"] = str(row.get("part_number", "UNKNOWN PART")).upper()
        else:
            row["name"] = str(row["name"]).upper()

        # --- Duplicate detection ---
        existing = _find_existing_part(row.get("part_number", ""), row.get("name", ""))
        if existing:
            # Part already exists — add imported quantity to its stock instead
            qty = row.get("quantity_on_hand", 0)
            if qty and qty > 0:
                record_stock_in(existing.part_id, qty, reason="Imported stock addition")
                all_warnings.append(
                    f"Row {i} ({existing.part_number} — {existing.name}): "
                    f"Already exists. Added {qty} unit(s) to existing stock."
                )
            else:
                all_warnings.append(
                    f"Row {i} ({existing.part_number} — {existing.name}): "
                    f"Already exists and no quantity to add — skipped."
                )
            merged += 1
            continue

        # --- New part — insert ---
        part = Part(
            part_id=None,
            part_number=str(row.get("part_number", "")).strip().upper(),
            name=str(row["name"]).strip().upper(),
            category=str(row.get("category", "") or "").strip().upper(),
            brand=str(row.get("brand", "") or "").strip().upper(),
            compatible_vehicles=str(row.get("compatible_vehicles", "") or "").strip().upper(),
            quantity_on_hand=row.get("quantity_on_hand", 0),
            cost_price=row.get("cost_price", 0.0),
            selling_price=row.get("selling_price", 0.0),
            reorder_level=row.get("reorder_level", 5),
            supplier_id=row.get("supplier_id")
        )
        success = add_part(part)
        if success:
            imported += 1
            for c in row.get("_corrections", []):
                all_warnings.append(f"Row {i} auto-corrected: {c}")
        else:
            all_errors.append(f"Row {i} ({row.get('part_number','?')}): Failed to insert (duplicate part number?).")
            skipped += 1

    return {
        "imported": imported,
        "merged": merged,
        "skipped": skipped,
        "warnings": all_warnings,
        "errors": all_errors,
        "rows": corrected
    }


def import_parts_from_excel(filepath: str) -> Dict[str, Any]:
    """
    Full pipeline: parse → auto-correct → import.
    Returns a report dict: {imported, skipped, warnings, errors}.
    """
    raw_rows, parse_warnings = parse_excel_file(filepath)
    if not raw_rows:
        return {"imported": 0, "skipped": 0, "warnings": parse_warnings, "errors": ["No data rows found."]}

    corrected = auto_correct_rows(raw_rows)
    return import_parts_from_rows(corrected, parse_warnings)
