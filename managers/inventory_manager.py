import sqlite3
import logging
from datetime import datetime
from typing import List, Optional
from database.db_manager import get_connection
from models.part import Part
from models.stock_movement import StockMovement
from typing import List, Optional, Tuple
from utils.validators import normalize_part_number, normalize_category

def add_part(part: Part) -> bool:
    """Adds a new part to the inventory."""
    part.part_number = normalize_part_number(part.part_number)
    part.name = (part.name or "").strip().upper()
    part.category = normalize_category(part.category)
    part.brand = (part.brand or "").strip().upper()
    part.compatible_vehicles = (part.compatible_vehicles or "").strip().upper()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Part (
                part_number, name, category, brand, compatible_vehicles, 
                quantity_on_hand, cost_price, selling_price, reorder_level, supplier_id,
                vehicle_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            part.part_number, part.name, part.category, part.brand, 
            part.compatible_vehicles, part.quantity_on_hand, part.cost_price, 
            part.selling_price, part.reorder_level, part.supplier_id,
            part.vehicle_type or "Car"
        ))
        conn.commit()
        
        # Note: If adding initial stock > 0, we should record a movement, 
        # but for simplicity, usually initial load is just set.
        if part.quantity_on_hand > 0:
            part.part_id = cursor.lastrowid
            _record_stock_movement(cursor, part.part_id, 'IN', part.quantity_on_hand, 'Initial Stock')
            conn.commit()

        logging.info(f"Part '{part.part_number}' added successfully.")
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"Failed to add part: Duplicate part_number '{part.part_number}'.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error adding part: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


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


def update_part(part: Part, user_id: int) -> bool:
    """Updates an existing part. Logs price changes."""
    part.part_number = normalize_part_number(part.part_number)
    part.name = (part.name or "").strip().upper()
    part.category = normalize_category(part.category)
    part.brand = (part.brand or "").strip().upper()
    part.compatible_vehicles = (part.compatible_vehicles or "").strip().upper()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Fetch old prices to see if we need to audit
        cursor.execute("SELECT cost_price, selling_price FROM Part WHERE part_id = ?", (part.part_id,))
        old_record = cursor.fetchone()
        
        if not old_record:
            return False

        old_cost = old_record["cost_price"]
        old_selling = old_record["selling_price"]

        cursor.execute("""
            UPDATE Part SET 
                part_number = ?, name = ?, category = ?, brand = ?, 
                compatible_vehicles = ?, reorder_level = ?, supplier_id = ?,
                cost_price = ?, selling_price = ?, vehicle_type = ?
            WHERE part_id = ?
        """, (
            part.part_number, part.name, part.category, part.brand,
            part.compatible_vehicles, part.reorder_level, part.supplier_id,
            part.cost_price, part.selling_price, part.vehicle_type or "Car",
            part.part_id
        ))

        # Audit price changes
        timestamp = datetime.now().isoformat()
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

        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error updating part {part.part_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


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

    Excludes deactivated parts by default (BR-02) — critically, this means
    a deactivated part can no longer be found and sold through POS.
    """
    conn = get_connection()
    cursor = conn.cursor()
    parts = []
    search_term = f"%{query}%"
    try:
        if include_inactive:
            cursor.execute("""
                SELECT * FROM Part
                WHERE part_number LIKE ? OR name LIKE ? OR category LIKE ? OR brand LIKE ?
            """, (search_term, search_term, search_term, search_term))
        else:
            cursor.execute("""
                SELECT * FROM Part
                WHERE (part_number LIKE ? OR name LIKE ? OR category LIKE ? OR brand LIKE ?)
                  AND name NOT LIKE '[DEACTIVATED]%'
            """, (search_term, search_term, search_term, search_term))

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
        cursor.execute("SELECT name FROM Part WHERE part_id = ?", (part_id,))
        row = cursor.fetchone()
        if not row:
            return False
            
        old_name = row["name"]
        if old_name.startswith("[DEACTIVATED]"):
            return True # already deactivated
            
        new_name = f"[DEACTIVATED] {old_name}"
        
        cursor.execute("UPDATE Part SET name = ? WHERE part_id = ?", (new_name, part_id))
        
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
    # vehicle_type may be absent on very old DBs before the migration runs;
    # fall back to 'Car' rather than raising a KeyError.
    try:
        vt = row["vehicle_type"] or "Car"
    except (IndexError, KeyError):
        vt = "Car"
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
        vehicle_type=vt,
    )
