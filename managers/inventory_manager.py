import sqlite3
import logging
from datetime import datetime
from typing import List, Optional
from database.db_manager import get_connection
from models.part import Part
from models.stock_movement import StockMovement
from typing import List, Optional, Tuple
from utils.validators import normalize_part_number, normalize_category

def add_part_detailed(part: Part) -> Tuple[bool, str]:
    """Adds a new part to the inventory and returns (success: bool, detail_message: str)."""
    part.part_number = normalize_part_number(part.part_number)
    part.name = (part.name or "").strip().upper()
    part.category = normalize_category(part.category)
    part.brand = (part.brand or "").strip().upper()
    part.compatible_vehicles = (part.compatible_vehicles or "").strip().upper()
    part.location = (part.location or "").strip().upper() or None

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check if an ACTIVE part with the same part_number already exists (case & whitespace insensitive)
        cursor.execute("""
            SELECT part_id, part_number, name FROM Part 
            WHERE UPPER(TRIM(part_number)) = UPPER(TRIM(?))
              AND name NOT LIKE '[DEACTIVATED]%'
        """, (part.part_number,))
        active_match = cursor.fetchone()
        if active_match:
            msg = f"Part Number '{part.part_number}' is already taken by active item '{active_match['name']}' (ID: {active_match['part_id']})."
            logging.warning(f"Failed to add part: {msg}")
            return False, msg

        # If deactivated parts exist with this part_number, rename them to release the unique constraint
        cursor.execute("""
            SELECT part_id, part_number FROM Part 
            WHERE UPPER(TRIM(part_number)) = UPPER(TRIM(?))
              AND name LIKE '[DEACTIVATED]%'
        """, (part.part_number,))
        for d_row in cursor.fetchall():
            d_id = d_row["part_id"]
            d_pn = d_row["part_number"]
            new_d_pn = f"[DEACTIVATED_{d_id}] {d_pn}" if not d_pn.startswith("[DEACTIVATED") else f"{d_pn}_{d_id}"
            cursor.execute("UPDATE Part SET part_number = ? WHERE part_id = ?", (new_d_pn, d_id))

        cursor.execute("""
            INSERT INTO Part (
                part_number, name, category, brand, compatible_vehicles, 
                quantity_on_hand, cost_price, selling_price, reorder_level, supplier_id,
                location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            part.part_number, part.name, part.category, part.brand, 
            part.compatible_vehicles, part.quantity_on_hand, part.cost_price, 
            part.selling_price, part.reorder_level, part.supplier_id,
            part.location
        ))
        conn.commit()
        
        part.part_id = cursor.lastrowid
        if part.quantity_on_hand > 0:
            _record_stock_movement(cursor, part.part_id, 'IN', part.quantity_on_hand, 'Initial Stock')
            conn.commit()

        logging.info(f"Part '{part.part_number}' added successfully (ID: {part.part_id}).")
        return True, f"Part '{part.part_number}' added successfully."
    except sqlite3.IntegrityError as e:
        msg = f"Database Integrity Error: {e}"
        logging.warning(f"Failed to add part '{part.part_number}': {msg}")
        return False, msg
    except sqlite3.Error as e:
        msg = f"Database Error: {e}"
        logging.error(f"Error adding part '{part.part_number}': {msg}")
        conn.rollback()
        return False, msg
    except Exception as e:
        msg = f"Unexpected Error: {e}"
        logging.error(f"Error adding part '{part.part_number}': {msg}")
        conn.rollback()
        return False, msg
    finally:
        conn.close()


def add_part(part: Part) -> bool:
    """Adds a new part to the inventory (returns bool for simple callers/tests)."""
    ok, _ = add_part_detailed(part)
    return ok


def bulk_update_category_prices(category_name: str, percentage_change: float) -> Tuple[bool, int]:
    """Adjusts selling prices for all parts in a category by a percentage (e.g. +5.0 or -3.0). Returns (success, count_updated)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        factor = 1.0 + (percentage_change / 100.0)
        if category_name == "All Categories" or not category_name:
            cursor.execute("UPDATE Part SET selling_price = ROUND(selling_price * ?, 2);", (factor,))
        else:
            cursor.execute(
                "UPDATE Part SET selling_price = ROUND(selling_price * ?, 2) WHERE UPPER(category) = UPPER(?);",
                (factor, category_name.strip())
            )
        count = cursor.rowcount
        conn.commit()
        logging.info(f"Bulk price update: {count} parts updated by {percentage_change}% in category '{category_name}'.")
        return True, count
    except sqlite3.Error as e:
        logging.error(f"Error bulk updating category prices: {e}")
        conn.rollback()
        return False, 0
    finally:
        conn.close()


def update_part_detailed(part: Part, user_id: int) -> Tuple[bool, str]:
    """Updates an existing part and returns (success: bool, detail_message: str)."""
    part.part_number = normalize_part_number(part.part_number)
    part.name = (part.name or "").strip().upper()
    part.category = normalize_category(part.category)
    part.brand = (part.brand or "").strip().upper()
    part.compatible_vehicles = (part.compatible_vehicles or "").strip().upper()
    part.location = (part.location or "").strip().upper() or None

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check if part_number changed and if it is already taken by another ACTIVE part (case & whitespace insensitive)
        cursor.execute("""
            SELECT part_id, name FROM Part 
            WHERE UPPER(TRIM(part_number)) = UPPER(TRIM(?))
              AND part_id != ?
              AND name NOT LIKE '[DEACTIVATED]%'
        """, (part.part_number, part.part_id))
        active_match = cursor.fetchone()
        if active_match:
            msg = f"Cannot update part: Part Number '{part.part_number}' is already taken by active item '{active_match['name']}' (ID: {active_match['part_id']})."
            logging.warning(msg)
            return False, msg

        # If deactivated parts (other than this one) exist with this part_number, rename them to release the unique constraint
        cursor.execute("""
            SELECT part_id, part_number FROM Part 
            WHERE UPPER(TRIM(part_number)) = UPPER(TRIM(?))
              AND part_id != ?
              AND name LIKE '[DEACTIVATED]%'
        """, (part.part_number, part.part_id))
        for d_row in cursor.fetchall():
            d_id = d_row["part_id"]
            d_pn = d_row["part_number"]
            new_d_pn = f"[DEACTIVATED_{d_id}] {d_pn}" if not d_pn.startswith("[DEACTIVATED") else f"{d_pn}_{d_id}"
            cursor.execute("UPDATE Part SET part_number = ? WHERE part_id = ?", (new_d_pn, d_id))

        # Fetch old prices and stock to see if we need to audit
        cursor.execute("SELECT cost_price, selling_price, quantity_on_hand FROM Part WHERE part_id = ?", (part.part_id,))
        old_record = cursor.fetchone()
        
        if not old_record:
            return False, f"Part ID {part.part_id} not found in database."

        old_cost = old_record["cost_price"]
        old_selling = old_record["selling_price"]
        old_qty = old_record["quantity_on_hand"]
        new_qty = part.quantity_on_hand if part.quantity_on_hand is not None else old_qty

        cursor.execute("""
            UPDATE Part SET 
                part_number = ?, name = ?, category = ?, brand = ?, 
                compatible_vehicles = ?, reorder_level = ?, supplier_id = ?,
                cost_price = ?, selling_price = ?, quantity_on_hand = ?,
                location = ?
            WHERE part_id = ?
        """, (
            part.part_number, part.name, part.category, part.brand,
            part.compatible_vehicles, part.reorder_level, part.supplier_id,
            part.cost_price, part.selling_price, new_qty,
            part.location, part.part_id
        ))

        timestamp = datetime.now().isoformat()

        # Audit price changes
        if old_cost != part.cost_price or old_selling != part.selling_price:
            cursor.execute("""
                INSERT INTO AuditLog (user_id, action, table_name, record_id, old_value, new_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, 'PRICE_CHANGE', 'Part', part.part_id, 
                f"Cost:{old_cost}, Sell:{old_selling}", 
                f"Cost:{part.cost_price}, Sell:{part.selling_price}", 
                timestamp
            ))

        # Audit stock quantity changes
        if new_qty != old_qty:
            delta = new_qty - old_qty
            movement_type = 'IN' if delta > 0 else 'OUT'
            _record_stock_movement(
                cursor, part.part_id, movement_type, abs(delta),
                'Initial Quantity Update' if old_qty == 0 else 'Manual Quantity Edit'
            )
            cursor.execute("""
                INSERT INTO AuditLog (user_id, action, table_name, record_id, old_value, new_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, 'ADJUSTMENT', 'Part', part.part_id, 
                f"qty:{old_qty}", f"qty:{new_qty}", 
                timestamp
            ))

        conn.commit()
        return True, f"Part '{part.part_number}' updated successfully."
    except sqlite3.IntegrityError as e:
        msg = f"Database Integrity Error updating part: {e}"
        logging.warning(msg)
        return False, msg
    except sqlite3.Error as e:
        msg = f"Database Error updating part: {e}"
        logging.error(msg)
        conn.rollback()
        return False, msg
    except Exception as e:
        msg = f"Unexpected Error updating part: {e}"
        logging.error(msg)
        conn.rollback()
        return False, msg
    finally:
        conn.close()


def update_part(part: Part, user_id: int) -> bool:
    """Updates an existing part (returns bool for simple callers/tests)."""
    ok, _ = update_part_detailed(part, user_id)
    return ok


def get_all_parts(include_inactive: bool = False) -> List[Part]:
    """Retrieves all parts in the inventory.

    By default, deactivated parts (BR-02) are excluded — this is what
    every normal screen (Inventory list, POS search) should call.
    Pass include_inactive=True only for admin views that specifically
    need to see deactivated parts (e.g. a future "show deactivated" toggle).
    """
    conn = get_connection()
    cursor = conn.cursor()
    parts = []
    try:
        if include_inactive:
            cursor.execute("SELECT * FROM Part;")
        else:
            cursor.execute("SELECT * FROM Part WHERE name NOT LIKE '[DEACTIVATED]%';")
        for row in cursor.fetchall():
            parts.append(_row_to_part(row))
        return parts
    except sqlite3.Error as e:
        logging.error(f"Database error fetching parts: {e}")
        return []
    finally:
        conn.close()


def search_parts(query: str, include_inactive: bool = False) -> List[Part]:
    """Searches parts by number, name, category, or brand.

    Excludes deactivated parts by default (BR-02).
    Results are sorted so exact part_number matches appear first, followed by
    part_number prefix matches, substring matches, and name matches.
    """
    conn = get_connection()
    cursor = conn.cursor()
    parts = []
    clean_q = (query or "").strip()
    search_term = f"%{clean_q}%"
    try:
        order_clause = """
            ORDER BY 
                CASE 
                    WHEN UPPER(TRIM(part_number)) = UPPER(?) THEN 1
                    WHEN UPPER(TRIM(part_number)) LIKE UPPER(?) || '%' THEN 2
                    WHEN UPPER(TRIM(part_number)) LIKE '%' || UPPER(?) || '%' THEN 3
                    WHEN UPPER(TRIM(name)) = UPPER(?) THEN 4
                    ELSE 5
                END,
                part_number ASC
        """
        if include_inactive:
            cursor.execute(f"""
                SELECT * FROM Part
                WHERE part_number LIKE ? OR name LIKE ? OR category LIKE ? OR brand LIKE ? OR location LIKE ?
                {order_clause}
            """, (search_term, search_term, search_term, search_term, search_term, clean_q, clean_q, clean_q, clean_q))
        else:
            cursor.execute(f"""
                SELECT * FROM Part
                WHERE (part_number LIKE ? OR name LIKE ? OR category LIKE ? OR brand LIKE ? OR location LIKE ?)
                  AND name NOT LIKE '[DEACTIVATED]%'
                {order_clause}
            """, (search_term, search_term, search_term, search_term, search_term, clean_q, clean_q, clean_q, clean_q))

        for row in cursor.fetchall():
            parts.append(_row_to_part(row))
        return parts
    except sqlite3.Error as e:
        logging.error(f"Database error searching parts: {e}")
        return []
    finally:
        conn.close()

def record_stock_in(part_id: int, quantity: int, reason: str = 'Purchase') -> bool:
    """Adds stock to a part and records the movement."""
    if quantity <= 0:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Update part quantity
        cursor.execute("""
            UPDATE Part SET quantity_on_hand = quantity_on_hand + ? 
            WHERE part_id = ?
        """, (quantity, part_id))
        
        # Record movement
        _record_stock_movement(cursor, part_id, 'IN', quantity, reason)
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error recording stock in for part {part_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def record_stock_adjustment(part_id: int, quantity_delta: int, reason: str, user_id: int) -> Tuple[bool, str]:
    """
    Manually adjusts a part's stock up or down (FR-15), e.g. after a physical
    stock take. quantity_delta can be positive (found extra stock) or negative
    (damaged/lost/miscounted). Enforces BR-01 (stock cannot go negative) and
    logs an AuditLog entry (FR-17).
    Returns (success, message).
    """
    if quantity_delta == 0:
        return False, "Adjustment quantity cannot be zero."
    if not reason or not reason.strip():
        return False, "A reason is required for a stock adjustment."

    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    try:
        cursor.execute("SELECT quantity_on_hand FROM Part WHERE part_id = ?", (part_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Part not found."

        old_qty = row["quantity_on_hand"]
        new_qty = old_qty + quantity_delta

        if new_qty < 0:
            return False, f"Adjustment would take stock negative (current: {old_qty}, change: {quantity_delta})."

        cursor.execute(
            "UPDATE Part SET quantity_on_hand = ? WHERE part_id = ?",
            (new_qty, part_id)
        )

        movement_type = 'IN' if quantity_delta > 0 else 'OUT'
        cursor.execute("""
            INSERT INTO StockMovement (part_id, movement_type, quantity, reason, timestamp)
            VALUES (?, ?, ?, 'Adjustment', ?)
        """, (part_id, movement_type, abs(quantity_delta), timestamp))

        cursor.execute("""
            INSERT INTO AuditLog (user_id, action, table_name, record_id, old_value, new_value, timestamp)
            VALUES (?, 'ADJUSTMENT', 'Part', ?, ?, ?, ?)
        """, (user_id, part_id, f"qty:{old_qty}", f"qty:{new_qty} ({reason.strip()})", timestamp))

        conn.commit()
        logging.info(f"Stock adjustment on part {part_id}: {old_qty} -> {new_qty} ({reason})")
        return True, f"Stock updated: {old_qty} -> {new_qty}."
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Database error adjusting stock for part {part_id}: {e}")
        return False, "A database error occurred during the adjustment."
    finally:
        conn.close()
        
def deactivate_part(part_id: int, user_id: int) -> bool:
    """Deactivates a part (removes it from search/catalogue without deleting history). 
       For now, we simulate this by renaming it or we could add an is_active flag.
       Since is_active is not in the schema, the BR-02 says "hidden from search".
       We will prepend '[DEACTIVATED] ' to the name as a quick workaround without schema changes.
    """
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    try:
        cursor.execute("SELECT name, part_number FROM Part WHERE part_id = ?", (part_id,))
        row = cursor.fetchone()
        if not row:
            return False
            
        old_name = row["name"]
        old_pn = row["part_number"]
        if old_name.startswith("[DEACTIVATED]"):
            return True # already deactivated
            
        new_name = f"[DEACTIVATED] {old_name}"
        new_pn = f"[DEACTIVATED_{part_id}] {old_pn}" if not old_pn.startswith("[DEACTIVATED") else old_pn
        
        cursor.execute("UPDATE Part SET name = ?, part_number = ? WHERE part_id = ?", (new_name, new_pn, part_id))
        
        # Audit deactivation
        cursor.execute("""
            INSERT INTO AuditLog (user_id, action, table_name, record_id, old_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, 'DEACTIVATE', 'Part', part_id, 
            old_name, new_name, timestamp
        ))

        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error deactivating part {part_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# --- Helper Methods ---

def _record_stock_movement(cursor, part_id: int, movement_type: str, quantity: int, reason: str):
    """Internal helper to insert a stock movement record (must be called within an active transaction)."""
    timestamp = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO StockMovement (part_id, movement_type, quantity, reason, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (part_id, movement_type, quantity, reason, timestamp))


def _row_to_part(row: sqlite3.Row) -> Part:
    """Internal helper to convert a database row to a Part object."""
    loc = row["location"] if "location" in row.keys() else None
    return Part(
        part_id=row["part_id"],
        part_number=row["part_number"],
        name=row["name"],
        category=row["category"],
        brand=row["brand"],
        compatible_vehicles=row["compatible_vehicles"],
        quantity_on_hand=row["quantity_on_hand"],
        cost_price=row["cost_price"],
        selling_price=row["selling_price"],
        reorder_level=row["reorder_level"],
        supplier_id=row["supplier_id"],
        location=loc
    )
