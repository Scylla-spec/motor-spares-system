import sqlite3
import logging
from datetime import datetime
from typing import List
from database.db_manager import get_connection
from models.purchase_order import PurchaseOrder
from utils.numbering import generate_po_number


def create_po(po: PurchaseOrder) -> bool:
    """Creates a new purchase order with a PO-YYYYMMDD-NNNN reference."""
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


def update_po_status(po_id: int, new_status: str) -> bool:
    """Updates the status of a PO. We don't automatically stock-in here yet."""
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
