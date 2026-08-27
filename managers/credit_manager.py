import sqlite3
import logging
from datetime import datetime
from typing import Tuple, List, Optional, Dict, Any
from database.db_manager import get_connection
from models.credit_order import CreditOrder, CreditOrderItem
from models.sale import Sale, SaleItem
from utils.numbering import generate_receipt_number


def create_credit_order(
    customer_name: str,
    items: List[Dict[str, Any]],
    cashier_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    customer_phone: Optional[str] = None,
    due_date: Optional[str] = None,
    notes: Optional[str] = None
) -> Tuple[bool, str, Optional[int]]:
    """
    Creates a new credit order, verifies & deducts part stock, and logs stock movements.
    Returns (success, message, credit_id).
    """
    if not customer_name.strip():
        return False, "Customer name is required.", None
    if not items:
        return False, "At least one item must be added to the credit order.", None

    total_amount = sum(item["quantity"] * item["unit_price"] for item in items)
    created_at = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Verify stock levels for all parts
        for item in items:
            cursor.execute("SELECT quantity_on_hand, name FROM Part WHERE part_id = ?", (item["part_id"],))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Part ID {item['part_id']} not found.")
            if row["quantity_on_hand"] < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for {row['name']}. Available: {row['quantity_on_hand']}, requested: {item['quantity']}"
                )

        # 2. Insert CreditOrder record
        cursor.execute("""
            INSERT INTO CreditOrder (
                customer_id, customer_name, customer_phone, total_amount,
                amount_paid, status, created_at, due_date, cashier_id, notes
            )
            VALUES (?, ?, ?, ?, 0.0, 'Pending', ?, ?, ?, ?)
        """, (
            customer_id, customer_name.strip(), customer_phone.strip() if customer_phone else None,
            total_amount, created_at, due_date, cashier_id, notes
        ))
        credit_id = cursor.lastrowid

        # 3. Insert items, deduct stock, and log stock movement
        for item in items:
            cursor.execute("""
                INSERT INTO CreditOrderItem (
                    credit_id, part_id, part_number, part_name, quantity, unit_price
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                credit_id, item["part_id"], item.get("part_number", ""),
                item.get("part_name", ""), item["quantity"], item["unit_price"]
            ))

            cursor.execute("""
                UPDATE Part SET quantity_on_hand = quantity_on_hand - ?
                WHERE part_id = ?
            """, (item["quantity"], item["part_id"]))

            cursor.execute("""
                INSERT INTO StockMovement (part_id, movement_type, quantity, reason, timestamp)
                VALUES (?, 'OUT', ?, ?, ?)
            """, (item["part_id"], item["quantity"], f"Credit Sale #{credit_id} ({customer_name})", created_at))

        conn.commit()
        logging.info(f"Credit Order #{credit_id} created for {customer_name}. Total: ${total_amount:.2f}")
        return True, f"Credit Order #{credit_id} recorded successfully.", credit_id

    except ValueError as ve:
        conn.rollback()
        logging.warning(f"Credit order validation failed: {ve}")
        return False, str(ve), None
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Database error during credit order creation: {e}")
        return False, f"Database error: {e}", None
    except Exception as e:
        conn.rollback()
        logging.error(f"Unexpected error during credit order: {e}")
        return False, str(e), None
    finally:
        conn.close()


def get_credit_orders(status_filter: Optional[str] = None) -> List[CreditOrder]:
    """Retrieves all credit orders, optionally filtered by status ('Pending' or 'Paid')."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if status_filter:
            cursor.execute("""
                SELECT * FROM CreditOrder
                WHERE status = ?
                ORDER BY created_at DESC
            """, (status_filter,))
        else:
            cursor.execute("""
                SELECT * FROM CreditOrder
                ORDER BY created_at DESC
            """)

        rows = cursor.fetchall()
        orders = []
        for r in rows:
            orders.append(CreditOrder(
                credit_id=r["credit_id"],
                customer_id=r["customer_id"],
                customer_name=r["customer_name"],
                customer_phone=r["customer_phone"],
                total_amount=r["total_amount"],
                amount_paid=r["amount_paid"],
                status=r["status"],
                created_at=r["created_at"],
                due_date=r["due_date"],
                paid_at=r["paid_at"],
                cashier_id=r["cashier_id"],
                notes=r["notes"]
            ))
        return orders
    finally:
        conn.close()


def get_credit_order_items(credit_id: int) -> List[CreditOrderItem]:
    """Retrieves all items for a given credit order."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM CreditOrderItem
            WHERE credit_id = ?
            ORDER BY item_id ASC
        """, (credit_id,))
        rows = cursor.fetchall()
        return [
            CreditOrderItem(
                item_id=r["item_id"],
                credit_id=r["credit_id"],
                part_id=r["part_id"],
                part_number=r["part_number"] or "",
                part_name=r["part_name"] or "",
                quantity=r["quantity"],
                unit_price=r["unit_price"]
            )
            for r in rows
        ]
    finally:
        conn.close()


def mark_credit_order_paid(
    credit_id: int,
    payment_method: str = "Cash",
    cashier_id: Optional[int] = None,
    cashier_name: str = "Cashier"
) -> Tuple[bool, str]:
    """
    Marks a pending credit order as Paid, updates paid timestamp, and records
    a completed Sale entry so revenue appears in sales reports.
    """
    conn = get_connection()
    cursor = conn.cursor()
    paid_at = datetime.now().isoformat()
    try:
        cursor.execute("SELECT * FROM CreditOrder WHERE credit_id = ?", (credit_id,))
        order = cursor.fetchone()
        if not order:
            return False, f"Credit Order #{credit_id} not found."
        if order["status"] == "Paid":
            return False, f"Credit Order #{credit_id} is already marked as Paid."

        total_amount = order["total_amount"]
        customer_id = order["customer_id"]

        # 1. Update CreditOrder to Paid
        cursor.execute("""
            UPDATE CreditOrder
            SET status = 'Paid', amount_paid = ?, paid_at = ?
            WHERE credit_id = ?
        """, (total_amount, paid_at, credit_id))

        # 2. Record sale into Sale and SaleItem tables for accounting
        cursor.execute("""
            INSERT INTO Sale (customer_id, total_amount, payment_method, timestamp, cashier_id)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_id, total_amount, payment_method, paid_at, cashier_id or order["cashier_id"] or 1))
        sale_id = cursor.lastrowid

        # Retrieve items
        cursor.execute("SELECT * FROM CreditOrderItem WHERE credit_id = ?", (credit_id,))
        items = cursor.fetchall()
        for it in items:
            cursor.execute("""
                INSERT INTO SaleItem (sale_id, part_id, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            """, (sale_id, it["part_id"], it["quantity"], it["unit_price"]))

        conn.commit()
        logging.info(f"Credit Order #{credit_id} settled successfully as Sale #{sale_id}.")
        return True, f"Credit Order #{credit_id} marked as Paid (${total_amount:.2f} via {payment_method})."

    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Error marking credit order as paid: {e}")
        return False, f"Database error: {e}"
    except Exception as e:
        conn.rollback()
        logging.error(f"Unexpected error settling credit order: {e}")
        return False, str(e)
    finally:
        conn.close()


def get_credit_summary() -> Dict[str, Any]:
    """Returns overview statistics for outstanding and settled credit."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as pending_count,
                COALESCE(SUM(total_amount - amount_paid), 0.0) as total_outstanding
            FROM CreditOrder
            WHERE status = 'Pending'
        """)
        pending_row = cursor.fetchone()

        cursor.execute("""
            SELECT 
                COUNT(*) as paid_count,
                COALESCE(SUM(amount_paid), 0.0) as total_paid
            FROM CreditOrder
            WHERE status = 'Paid'
        """)
        paid_row = cursor.fetchone()

        return {
            "pending_count": pending_row["pending_count"] if pending_row else 0,
            "total_outstanding": pending_row["total_outstanding"] if pending_row else 0.0,
            "paid_count": paid_row["paid_count"] if paid_row else 0,
            "total_paid": paid_row["total_paid"] if paid_row else 0.0,
        }
    finally:
        conn.close()
