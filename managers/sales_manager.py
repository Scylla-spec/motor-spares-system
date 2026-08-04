import sqlite3
import logging
from datetime import datetime
from typing import Tuple, List
from database.db_manager import get_connection
from models.sale import Sale, SaleItem
from utils.receipt_generator import generate_pdf_receipt
from utils.numbering import generate_receipt_number


def process_sale(cart_items: List[SaleItem], payment_method: str, cashier_id: int,
                 cashier_name: str, customer_id: int = None, customer_name: str = "Walk-in") -> Tuple[bool, str]:
    """
    Processes a sale, deducting stock and creating database records in a transaction.
    Returns (success_boolean, receipt_path_or_error_message).
    """
    if not cart_items:
        return False, "Cart is empty."

    total_amount = sum(item.subtotal for item in cart_items)
    timestamp = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Verify stock levels for all items first (BR-01, BR-06)
        for item in cart_items:
            cursor.execute("SELECT quantity_on_hand FROM Part WHERE part_id = ?", (item.part_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Part ID {item.part_id} not found.")
            if row["quantity_on_hand"] < item.quantity:
                raise ValueError(f"Insufficient stock for {item.part_name}. Available: {row['quantity_on_hand']}")

        # 2. Generate receipt number before insert (REC-YYYYMMDD-NNNN, daily sequence)
        receipt_number = generate_receipt_number(cursor)

        # 3. Insert Sale Record
        cursor.execute("""
            INSERT INTO Sale (customer_id, total_amount, payment_method, timestamp, cashier_id)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_id, total_amount, payment_method, timestamp, cashier_id))
        sale_id = cursor.lastrowid

        # 4. Insert Sale Items and Deduct Stock
        for item in cart_items:
            cursor.execute("""
                INSERT INTO SaleItem (sale_id, part_id, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            """, (sale_id, item.part_id, item.quantity, item.unit_price))

            cursor.execute("""
                UPDATE Part SET quantity_on_hand = quantity_on_hand - ?
                WHERE part_id = ?
            """, (item.quantity, item.part_id))

            cursor.execute("""
                INSERT INTO StockMovement (part_id, movement_type, quantity, reason, timestamp)
                VALUES (?, 'OUT', ?, 'Sale', ?)
            """, (item.part_id, item.quantity, timestamp))

        conn.commit()
        logging.info(f"Sale {sale_id} processed successfully. Total: ${total_amount:.2f}")

        sale_record = Sale(
            sale_id=sale_id,
            total_amount=total_amount,
            payment_method=payment_method,
            timestamp=timestamp,
            cashier_id=cashier_id,
            customer_id=customer_id,
            items=cart_items
        )
        receipt_path = generate_pdf_receipt(sale_record, receipt_number, cashier_name, customer_name)

        return True, receipt_path

    except ValueError as ve:
        conn.rollback()
        logging.warning(f"Sale failed validation: {ve}")
        return False, str(ve)
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Database error during sale: {e}")
        return False, "A database error occurred during checkout."
    except Exception as e:
        conn.rollback()
        logging.error(f"Unexpected error during sale: {e}")
        return False, "An unexpected error occurred."
    finally:
        conn.close()
