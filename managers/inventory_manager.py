import sqlite3
import logging
from datetime import datetime
from typing import List, Optional
from database.db_manager import get_connection
from models.part import Part
from models.stock_movement import StockMovement

def add_part(part: Part) -> bool:
    """Adds a new part to the inventory."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Part (
                part_number, name, category, brand, compatible_vehicles, 
                quantity_on_hand, cost_price, selling_price, reorder_level, supplier_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            part.part_number, part.name, part.category, part.brand, 
            part.compatible_vehicles, part.quantity_on_hand, part.cost_price, 
            part.selling_price, part.reorder_level, part.supplier_id
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


def update_part(part: Part, user_id: int) -> bool:
    """Updates an existing part. Logs price changes."""
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
                cost_price = ?, selling_price = ?
            WHERE part_id = ?
        """, (
            part.part_number, part.name, part.category, part.brand,
            part.compatible_vehicles, part.reorder_level, part.supplier_id,
            part.cost_price, part.selling_price, part.part_id
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


def get_all_parts() -> List[Part]:
    """Retrieves all parts in the inventory."""
    conn = get_connection()
    cursor = conn.cursor()
    parts = []
    try:
        cursor.execute("SELECT * FROM Part;")
        for row in cursor.fetchall():
            parts.append(_row_to_part(row))
        return parts
    except sqlite3.Error as e:
        logging.error(f"Database error fetching parts: {e}")
        return []
    finally:
        conn.close()


def search_parts(query: str) -> List[Part]:
    """Searches parts by number, name, category, or brand."""
    conn = get_connection()
    cursor = conn.cursor()
    parts = []
    search_term = f"%{query}%"
    try:
        cursor.execute("""
            SELECT * FROM Part 
            WHERE part_number LIKE ? OR name LIKE ? OR category LIKE ? OR brand LIKE ?
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
        supplier_id=row["supplier_id"]
    )
