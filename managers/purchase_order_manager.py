import sqlite3
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from database.db_manager import get_connection
from models.purchase_order import PurchaseOrder, PurchaseOrderItem
from utils.numbering import generate_po_number


def create_po(po: PurchaseOrder) -> bool:
    """Legacy helper: Creates a simple purchase order."""
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d")
    try:
        po_number = generate_po_number(cursor)
        cursor.execute("""
            INSERT INTO PurchaseOrder (supplier_id, status, order_date, total_cost, po_number)
            VALUES (?, ?, ?, ?, ?)
        """, (po.supplier_id, po.status, timestamp, po.total_cost, po_number))
        conn.commit()
        po.po_id = cursor.lastrowid
        po.order_date = timestamp
        po.po_number = po_number
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error creating PO: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def create_po_with_items(
    supplier_id: int,
    items: List[Dict[str, Any]],
    status: str = "Ordered"
) -> Tuple[bool, str, Optional[int]]:
    """
    Creates a new purchase order with itemized line items.
    
    `items` is expected to be a list of dicts:
    [
        {"part_id": 1, "part_number": "BP001", "part_name": "Front Brake Pad", "quantity_ordered": 10, "unit_cost": 15.00},
        ...
    ]
    """
    if not items:
        return False, "A purchase order must contain at least one item.", None

    total_cost = sum(item["quantity_ordered"] * item["unit_cost"] for item in items)
    timestamp = datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        po_number = generate_po_number(cursor)
        cursor.execute("""
            INSERT INTO PurchaseOrder (supplier_id, status, order_date, total_cost, po_number)
            VALUES (?, ?, ?, ?, ?)
        """, (supplier_id, status, timestamp, total_cost, po_number))
        po_id = cursor.lastrowid

        for it in items:
            qty = it["quantity_ordered"]
            cost = it["unit_cost"]
            subtotal = qty * cost
            cursor.execute("""
                INSERT INTO PurchaseOrderItem (po_id, part_id, part_number, part_name, quantity_ordered, unit_cost, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (po_id, it["part_id"], it.get("part_number", ""), it.get("part_name", ""), qty, cost, subtotal))

        conn.commit()
        logging.info(f"Created Purchase Order #{po_id} ({po_number}) with {len(items)} items. Total: ${total_cost:.2f}")
        return True, po_number, po_id

    except sqlite3.Error as e:
        logging.error(f"Database error creating itemized PO: {e}")
        conn.rollback()
        return False, str(e), None
    finally:
        conn.close()


def get_po_items(po_id: int) -> List[PurchaseOrderItem]:
    """Retrieves all line items for a specific purchase order."""
    conn = get_connection()
    cursor = conn.cursor()
    items = []
    try:
        cursor.execute("""
            SELECT po_item_id, po_id, part_id, part_number, part_name, quantity_ordered, unit_cost, subtotal
            FROM PurchaseOrderItem
            WHERE po_id = ?
            ORDER BY po_item_id ASC
        """, (po_id,))
        for row in cursor.fetchall():
            items.append(PurchaseOrderItem(
                po_item_id=row["po_item_id"],
                po_id=row["po_id"],
                part_id=row["part_id"],
                part_number=row["part_number"] or "",
                part_name=row["part_name"] or "",
                quantity_ordered=row["quantity_ordered"],
                unit_cost=row["unit_cost"],
                subtotal=row["subtotal"]
            ))
        return items
    except sqlite3.Error as e:
        logging.error(f"Database error fetching PO items for PO #{po_id}: {e}")
        return []
    finally:
        conn.close()


def get_po_by_id(po_id: int) -> Optional[PurchaseOrder]:
    """Retrieves a single purchase order by ID, including its supplier details and line items."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT po.po_id, po.supplier_id, po.status, po.order_date, po.total_cost,
                   po.po_number, s.name as supplier_name
            FROM PurchaseOrder po
            JOIN Supplier s ON po.supplier_id = s.supplier_id
            WHERE po.po_id = ?
        """, (po_id,))
        row = cursor.fetchone()
        if not row:
            return None
        po = PurchaseOrder(
            po_id=row["po_id"],
            supplier_id=row["supplier_id"],
            status=row["status"],
            order_date=row["order_date"],
            total_cost=row["total_cost"],
            po_number=row["po_number"] or "",
            supplier_name=row["supplier_name"],
            items=get_po_items(po_id)
        )
        return po
    except sqlite3.Error as e:
        logging.error(f"Database error fetching PO #{po_id}: {e}")
        return None
    finally:
        conn.close()


def receive_po_stock(po_id: int) -> Tuple[bool, str]:
    """
    Receives all items in a Purchase Order:
    1. Validates that the PO exists and is not already 'Received'.
    2. Increments warehouse quantity_on_hand for all line items.
    3. Records official StockMovement (type='IN', reason='PO Received: PO-...') for each item.
    4. Updates the PO status to 'Received'.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT po_id, status, po_number FROM PurchaseOrder WHERE po_id = ?", (po_id,))
        po_row = cursor.fetchone()
        if not po_row:
            return False, "Purchase order not found."

        if po_row["status"] == "Received":
            return False, f"Purchase order {po_row['po_number'] or po_id} has already been received."

        po_number = po_row["po_number"] or f"PO-#{po_id}"
        timestamp = datetime.now().isoformat()

        # Fetch items
        cursor.execute("""
            SELECT part_id, quantity_ordered, unit_cost FROM PurchaseOrderItem WHERE po_id = ?
        """, (po_id,))
        items = cursor.fetchall()

        if not items:
            # If it's a legacy PO without itemized records, just update status
            cursor.execute("UPDATE PurchaseOrder SET status = 'Received' WHERE po_id = ?", (po_id,))
            conn.commit()
            return True, f"Purchase order {po_number} marked as Received."

        for item in items:
            part_id = item["part_id"]
            qty = item["quantity_ordered"]

            # Update inventory quantity
            cursor.execute("""
                UPDATE Part
                SET quantity_on_hand = quantity_on_hand + ?
                WHERE part_id = ?
            """, (qty, part_id))

            # Record stock movement audit log
            cursor.execute("""
                INSERT INTO StockMovement (part_id, movement_type, quantity, reason, timestamp)
                VALUES (?, 'IN', ?, ?, ?)
            """, (part_id, qty, f"PO Received: {po_number}", timestamp))

        # Update PO status
        cursor.execute("UPDATE PurchaseOrder SET status = 'Received' WHERE po_id = ?", (po_id,))
        conn.commit()
        logging.info(f"Successfully received stock for PO #{po_id} ({po_number}) with {len(items)} items.")
        return True, f"Purchase order {po_number} successfully received and warehouse stock updated!"

    except sqlite3.Error as e:
        logging.error(f"Database error receiving PO stock for PO #{po_id}: {e}")
        conn.rollback()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def update_po_status(po_id: int, new_status: str) -> bool:
    """Updates the status of a PO."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE PurchaseOrder SET status = ? WHERE po_id = ?", (new_status, po_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error updating PO status: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_all_pos() -> List[PurchaseOrder]:
    """Retrieves all purchase orders with supplier names attached."""
    conn = get_connection()
    cursor = conn.cursor()
    pos = []
    try:
        cursor.execute("""
            SELECT po.po_id, po.supplier_id, po.status, po.order_date, po.total_cost,
                   po.po_number, s.name as supplier_name
            FROM PurchaseOrder po
            JOIN Supplier s ON po.supplier_id = s.supplier_id
            ORDER BY po.po_id DESC
        """)
        for row in cursor.fetchall():
            pos.append(PurchaseOrder(
                po_id=row["po_id"],
                supplier_id=row["supplier_id"],
                status=row["status"],
                order_date=row["order_date"],
                total_cost=row["total_cost"],
                po_number=row["po_number"] or "",
                supplier_name=row["supplier_name"]
            ))
        return pos
    except sqlite3.Error as e:
        logging.error(f"Database error fetching POs: {e}")
        return []
    finally:
        conn.close()


def get_low_stock_parts_for_reorder() -> List[Dict[str, Any]]:
    """Retrieves all active parts that are currently at or below their reorder level."""
    conn = get_connection()
    cursor = conn.cursor()
    low_stock = []
    try:
        cursor.execute("""
            SELECT part_id, part_number, name, category, brand, cost_price,
                   selling_price, quantity_on_hand, reorder_level,
                   (reorder_level - quantity_on_hand) as shortage
            FROM Part
            WHERE quantity_on_hand <= reorder_level
              AND name NOT LIKE '[DEACTIVATED]%'
            ORDER BY shortage DESC, name ASC
        """)
        for row in cursor.fetchall():
            reorder_qty = max(10, row["shortage"] + 5)  # Suggested reorder quantity
            low_stock.append({
                "part_id": row["part_id"],
                "part_number": row["part_number"],
                "name": row["name"],
                "category": row["category"],
                "brand": row["brand"],
                "cost_price": row["cost_price"],
                "quantity_on_hand": row["quantity_on_hand"],
                "reorder_level": row["reorder_level"],
                "suggested_qty": reorder_qty
            })
        return low_stock
    except sqlite3.Error as e:
        logging.error(f"Database error fetching low stock parts for reorder: {e}")
        return []
    finally:
        conn.close()
