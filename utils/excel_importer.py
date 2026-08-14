"""
Excel Bulk Import Utility
=========================
Reads .xlsx files, auto-corrects common formatting/spelling errors,
and imports parts into the inventory.
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
                             "code", "item code", "sku", "stock code", "part#"],
    "name":                ["name", "description", "part name", "item name", "item description",
                             "product name", "part description"],
    "category":            ["category", "cat", "type", "group", "product type"],
    "brand":               ["brand", "manufacturer", "make", "mfr", "mfg"],
    "compatible_vehicles": ["compatible vehicles", "vehicles", "fits", "vehicle",
                             "compatibility", "application", "for vehicle"],
    "cost_price":          ["cost price", "cost", "buy price", "purchase price", "unit cost",
                             "buying price", "net price"],
    "selling_price":       ["selling price", "sell price", "sale price", "retail price",
                             "price", "unit price", "rrp"],
    "quantity_on_hand":    ["quantity", "qty", "stock", "quantity on hand", "on hand",
                             "stock qty", "stock quantity", "units"],
    "reorder_level":       ["reorder level", "reorder", "min stock", "minimum stock",
                             "reorder point", "min qty"],
    "supplier":            ["supplier", "vendor", "supplier name"],
}

def _normalise(text: str) -> str:
    """Lowercase, strip whitespace for comparison."""
    return str(text).lower().strip()

def _map_headers(headers: List[str]) -> Dict[str, int]:
    """
    Maps raw spreadsheet headers to canonical field names.
    Returns {canonical_field: column_index}.
    """
    mapping = {}
    normalised_headers = [_normalise(h) for h in headers]
    
    for field, aliases in COLUMN_ALIASES.items():
        for idx, header in enumerate(normalised_headers):
            if header in aliases:
                mapping[field] = idx
                break
    return mapping

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

def parse_excel_file(filepath: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses an Excel file and returns:
    - list of raw row dicts with canonical field names
    - list of header-mapping warnings
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], ["The spreadsheet appears to be empty."]
    
    # Find header row — first non-empty row
    header_row_idx = 0
    for i, row in enumerate(rows):
        if any(cell is not None for cell in row):
            header_row_idx = i
            break
    
    headers = [str(h) if h is not None else "" for h in rows[header_row_idx]]
    col_map = _map_headers(headers)
    
    warnings = []
    required = ["part_number", "name"]
    for req in required:
        if req not in col_map:
            warnings.append(f"⚠ Could not find a '{req}' column. Recognised aliases: {COLUMN_ALIASES[req][:4]}")
    
    parsed_rows = []
    for row in rows[header_row_idx + 1:]:
        if all(cell is None for cell in row):
            continue  # skip empty rows
        
        record = {}
        for field, col_idx in col_map.items():
            record[field] = row[col_idx] if col_idx < len(row) else None
            
        parsed_rows.append(record)
    
    return parsed_rows, warnings

def auto_correct_rows(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Applies auto-correction to each row:
    - Cleans numeric fields
    - Fuzzy-corrects category/brand/supplier against existing DB values
    - Adds '_warnings' and '_corrections' keys per row
    """
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
        clean["part_number"] = str(clean.get("part_number", "")).strip().upper()
        
        # --- Name ---
        name = str(clean.get("name", "")).strip()
        if name:
            name = name.strip().title()
        clean["name"] = name

        # --- Category: fuzzy correct ---
        raw_cat = str(clean.get("category", "")).strip()
        if raw_cat:
            fixed_cat, was_fixed = _fuzzy_correct(raw_cat, existing_categories)
            if was_fixed:
                corrections.append(f"Category: '{raw_cat}' → '{fixed_cat}'")
            clean["category"] = fixed_cat
        else:
            clean["category"] = raw_cat

        # --- Brand: fuzzy correct ---
        raw_brand = str(clean.get("brand", "")).strip()
        if raw_brand:
            fixed_brand, was_fixed = _fuzzy_correct(raw_brand, existing_brands)
            if was_fixed:
                corrections.append(f"Brand: '{raw_brand}' → '{fixed_brand}'")
            clean["brand"] = fixed_brand
        else:
            clean["brand"] = raw_brand

        # --- Compatible Vehicles ---
        clean["compatible_vehicles"] = str(clean.get("compatible_vehicles", "") or "").strip()

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

        # --- Validation errors ---
        errors = []
        if not clean.get("part_number"):
            errors.append("Part Number is missing.")
        if not clean.get("name"):
            errors.append("Name is missing.")
        if clean.get("cost_price", 0) < 0:
            errors.append("Cost price cannot be negative.")

        clean["_warnings"] = warnings
        clean["_corrections"] = corrections
        clean["_errors"] = errors
        corrected_rows.append(clean)

    return corrected_rows

def import_parts_from_rows(corrected: List[Dict[str, Any]], parse_warnings: List[str] = None) -> Dict[str, Any]:
    """
    Commits already-parsed-and-corrected rows to inventory. This is the
    shared tail end used by both Excel import and Image/OCR import (FR-19)
    \u2014 and critically, it's what lets a user's manual corrections in the
    review table actually get committed, instead of the import silently
    re-reading the original source file from scratch.
    """
    imported = 0
    skipped = 0
    all_warnings = list(parse_warnings or [])
    all_errors = []

    for i, row in enumerate(corrected, start=1):
        if row.get("_errors"):
            all_errors.append(f"Row {i} ({row.get('part_number','?')}): {'; '.join(row['_errors'])}")
            skipped += 1
            continue

        part = Part(
            part_id=None,
            part_number=row["part_number"],
            name=row["name"],
            category=row.get("category", ""),
            brand=row.get("brand", ""),
            compatible_vehicles=row.get("compatible_vehicles", ""),
            quantity_on_hand=row["quantity_on_hand"],
            cost_price=row["cost_price"],
            selling_price=row["selling_price"],
            reorder_level=row["reorder_level"],
            supplier_id=row.get("supplier_id")
        )
        success = add_part(part)
        if success:
            imported += 1
            for c in row.get("_corrections", []):
                all_warnings.append(f"Row {i} auto-corrected: {c}")
        else:
            all_errors.append(f"Row {i} ({row['part_number']}): Failed to insert (duplicate part number?).")
            skipped += 1

    return {
        "imported": imported,
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
