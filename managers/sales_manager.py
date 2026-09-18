import sqlite3
import logging
from datetime import datetime
from typing import Tuple, List, Optional
from database.db_manager import get_connection
from models.sale import Sale, SaleItem
from utils.receipt_generator import generate_pdf_receipt
from utils.thermal_receipt import print_thermal_receipt
from utils.numbering import generate_receipt_number


def process_sale(
    cart_items: List[SaleItem],
    payment_method: str,
    cashier_id: int,
    cashier_name: str,
    customer_id: int = None,
    customer_name: str = "Walk-in",
    currency: str = "USD",
    exchange_rate: float = 1.0,
    amount_paid_curr: Optional[float] = None,
) -> Tuple[bool, str]:
    """
    Processes a sale, deducting stock and creating database records in a transaction.

    Args:
        cart_items:        List of SaleItem objects (unit_price is the negotiated/final price,
                           original_unit_price is the catalogue price before negotiation).
        payment_method:    'Cash', 'EcoCash', or 'Card'.
        cashier_id:        User ID of the cashier performing the sale.
        cashier_name:      Display name for the receipt.
        customer_id:       Optional Customer record ID.
        customer_name:     Display name for the receipt.
        currency:          Settlement currency chosen at checkout ('USD', 'ZAR', 'ZIG').
        exchange_rate:     Rate applied at checkout (1 USD = X currency units).
        amount_paid_curr:  Total amount in the settlement currency (for receipt display).

    Returns:
        (success_boolean, receipt_path_or_error_message)
    """
    if not cart_items:
        return False, "Cart is empty."

    # Total amount is always stored in base USD
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

        # 3. Insert Sale Record (with multi-currency columns)
        cursor.execute("""
            INSERT INTO Sale (customer_id, total_amount, payment_method, timestamp, cashier_id,
                              currency, exchange_rate, amount_paid_curr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (customer_id, total_amount, payment_method, timestamp, cashier_id,
              currency, exchange_rate, amount_paid_curr))
        sale_id = cursor.lastrowid

        # 4. Insert Sale Items and Deduct Stock
        for item in cart_items:
            # Persist both the negotiated price and the original catalogue price
            orig_price = item.original_unit_price if item.original_unit_price is not None else item.unit_price
            cursor.execute("""
                INSERT INTO SaleItem (sale_id, part_id, quantity, unit_price, original_unit_price)
                VALUES (?, ?, ?, ?, ?)
            """, (sale_id, item.part_id, item.quantity, item.unit_price, orig_price))

            cursor.execute("""
                UPDATE Part SET quantity_on_hand = quantity_on_hand - ?
                WHERE part_id = ?
            """, (item.quantity, item.part_id))

            cursor.execute("""
                INSERT INTO StockMovement (part_id, movement_type, quantity, reason, timestamp)
                VALUES (?, 'OUT', ?, 'Sale', ?)
            """, (item.part_id, item.quantity, timestamp))

            # 5. Audit-log price negotiation if the cashier overrode the list price
            if item.was_negotiated:
                cursor.execute("""
                    INSERT INTO AuditLog (user_id, action, table_name, record_id,
                                         old_value, new_value, timestamp)
                    VALUES (?, 'PRICE_CHANGE', 'SaleItem', ?, ?, ?, ?)
                """, (
                    cashier_id,
                    sale_id,
                    f"List ${orig_price:.2f}",
                    f"Negotiated ${item.unit_price:.2f} (Part {item.part_number})",
                    timestamp,
                ))

        conn.commit()
        logging.info(f"Sale {sale_id} processed. Total: ${total_amount:.2f} | Currency: {currency} @ {exchange_rate}")

        sale_record = Sale(
            sale_id=sale_id,
            total_amount=total_amount,
            payment_method=payment_method,
            timestamp=timestamp,
            cashier_id=cashier_id,
            customer_id=customer_id,
            items=cart_items,
            currency=currency,
            exchange_rate=exchange_rate,
            amount_paid_curr=amount_paid_curr,
        )
        receipt_path = generate_pdf_receipt(sale_record, receipt_number, cashier_name, customer_name)

        # Print thermal receipt (supermarket-style)
        try:
            print_thermal_receipt(sale_record, receipt_number, cashier_name, customer_name)
        except Exception as th_err:
            logging.warning(f"Thermal receipt printing error: {th_err}")

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

