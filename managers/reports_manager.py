import sqlite3
import logging
from typing import List, Dict, Any
from database.db_manager import get_connection

def get_daily_transactions(date_str: str) -> List[Dict[str, Any]]:
    """
    Returns every transaction made on a specific date (YYYY-MM-DD),
    including time, customer, cashier, items summary, payment method, and amount.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT s.sale_id,
                   s.timestamp,
                   s.total_amount,
                   s.payment_method,
                   COALESCE(c.name, 'Walk-in') as customer_name,
                   COALESCE(u.username, 'Unknown') as cashier_name,
                   GROUP_CONCAT(p.name || ' (x' || si.quantity || ')', ', ') as items_summary,
                   COALESCE(SUM(si.quantity), 0) as total_items
            FROM Sale s
            LEFT JOIN Customer c ON s.customer_id = c.customer_id
            LEFT JOIN User u ON s.cashier_id = u.user_id
            LEFT JOIN SaleItem si ON s.sale_id = si.sale_id
            LEFT JOIN Part p ON si.part_id = p.part_id
            WHERE date(s.timestamp) = ?
            GROUP BY s.sale_id
            ORDER BY s.timestamp DESC
        """, (date_str,))

        transactions = []
        for row in cursor.fetchall():
            raw_time = row["timestamp"] or ""
            if "T" in raw_time:
                time_str = raw_time.split("T")[1][:8]
            elif " " in raw_time:
                time_str = raw_time.split(" ")[1][:8]
            else:
                time_str = raw_time

            transactions.append({
                "sale_id": row["sale_id"],
                "receipt_no": f"REC-{row['sale_id']:05d}",
                "timestamp": raw_time,
                "time": time_str,
                "customer_name": row["customer_name"],
                "cashier_name": row["cashier_name"],
                "payment_method": row["payment_method"],
                "total_amount": float(row["total_amount"]),
                "items_summary": row["items_summary"] or "Standard sale",
                "total_items": row["total_items"]
            })
        return transactions
    except sqlite3.Error as e:
        logging.error(f"Error in get_daily_transactions: {e}")
        return []
    finally:
        conn.close()


def get_daily_sales_summary(date_str: str) -> Dict[str, Any]:
    """
    Returns summary and detailed transaction list for a specific date (YYYY-MM-DD).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) as transaction_count,
                   COALESCE(SUM(total_amount), 0) as total_revenue,
                   COALESCE(SUM(CASE WHEN payment_method = 'Cash' THEN total_amount ELSE 0 END), 0) as cash_revenue,
                   COALESCE(SUM(CASE WHEN payment_method = 'EcoCash' THEN total_amount ELSE 0 END), 0) as ecocash_revenue,
                   COALESCE(SUM(CASE WHEN payment_method = 'Card' THEN total_amount ELSE 0 END), 0) as card_revenue
            FROM Sale
            WHERE date(timestamp) = ?
        """, (date_str,))
        row = cursor.fetchone()

        transactions = get_daily_transactions(date_str)
        total_items = sum(t["total_items"] for t in transactions)

        return {
            "date": date_str,
            "transaction_count": row["transaction_count"],
            "total_revenue": row["total_revenue"],
            "cash_revenue": row["cash_revenue"],
            "ecocash_revenue": row["ecocash_revenue"],
            "card_revenue": row["card_revenue"],
            "total_items": total_items,
            "transactions": transactions
        }
    except sqlite3.Error as e:
        logging.error(f"Error in get_daily_sales_summary: {e}")
        return {
            "date": date_str, "transaction_count": 0, "total_revenue": 0.0,
            "cash_revenue": 0.0, "ecocash_revenue": 0.0, "card_revenue": 0.0,
            "total_items": 0, "transactions": []
        }
    finally:
        conn.close()


def get_monthly_transactions(year: int, month: int) -> List[Dict[str, Any]]:
    """
    Returns every individual transaction made in a given month (YYYY-MM).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        month_str = f"{year:04d}-{month:02d}"
        cursor.execute("""
            SELECT s.sale_id,
                   s.timestamp,
                   date(s.timestamp) as sale_date,
                   s.total_amount,
                   s.payment_method,
                   COALESCE(c.name, 'Walk-in') as customer_name,
                   COALESCE(u.username, 'Unknown') as cashier_name,
                   GROUP_CONCAT(p.name || ' (x' || si.quantity || ')', ', ') as items_summary,
                   COALESCE(SUM(si.quantity), 0) as total_items
            FROM Sale s
            LEFT JOIN Customer c ON s.customer_id = c.customer_id
            LEFT JOIN User u ON s.cashier_id = u.user_id
            LEFT JOIN SaleItem si ON s.sale_id = si.sale_id
            LEFT JOIN Part p ON si.part_id = p.part_id
            WHERE strftime('%Y-%m', s.timestamp) = ?
            GROUP BY s.sale_id
            ORDER BY s.timestamp DESC
        """, (month_str,))

        transactions = []
        for row in cursor.fetchall():
            raw_time = row["timestamp"] or ""
            if "T" in raw_time:
                time_str = raw_time.split("T")[1][:8]
            elif " " in raw_time:
                time_str = raw_time.split(" ")[1][:8]
            else:
                time_str = raw_time

            transactions.append({
                "sale_id": row["sale_id"],
                "receipt_no": f"REC-{row['sale_id']:05d}",
                "date": row["sale_date"],
                "timestamp": raw_time,
                "time": time_str,
                "customer_name": row["customer_name"],
                "cashier_name": row["cashier_name"],
                "payment_method": row["payment_method"],
                "total_amount": float(row["total_amount"]),
                "items_summary": row["items_summary"] or "Standard sale",
                "total_items": row["total_items"]
            })
        return transactions
    except sqlite3.Error as e:
        logging.error(f"Error in get_monthly_transactions: {e}")
        return []
    finally:
        conn.close()


def get_monthly_sales_summary(year: int, month: int) -> List[Dict[str, Any]]:
    """
    Returns day-by-day sales breakdown for a given month.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        month_str = f"{year:04d}-{month:02d}"
        cursor.execute("""
            SELECT date(timestamp) as sale_date,
                   COUNT(*) as transaction_count,
                   COALESCE(SUM(total_amount), 0) as total_revenue,
                   COALESCE(SUM(CASE WHEN payment_method = 'Cash' THEN total_amount ELSE 0 END), 0) as cash_revenue,
                   COALESCE(SUM(CASE WHEN payment_method = 'EcoCash' THEN total_amount ELSE 0 END), 0) as ecocash_revenue,
                   COALESCE(SUM(CASE WHEN payment_method = 'Card' THEN total_amount ELSE 0 END), 0) as card_revenue
            FROM Sale
            WHERE strftime('%Y-%m', timestamp) = ?
            GROUP BY sale_date
            ORDER BY sale_date
        """, (month_str,))
        return [
            {
                "date": row["sale_date"],
                "transaction_count": row["transaction_count"],
                "total_revenue": row["total_revenue"],
                "cash_revenue": row["cash_revenue"],
                "ecocash_revenue": row["ecocash_revenue"],
                "card_revenue": row["card_revenue"],
            }
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        logging.error(f"Error in get_monthly_sales_summary: {e}")
        return []
    finally:
        conn.close()

def get_top_selling_parts(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Returns top-selling parts ranked by total quantity sold.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.part_number, p.name, p.brand, p.category,
                   COALESCE(SUM(si.quantity), 0) as total_qty_sold,
                   COALESCE(SUM(si.quantity * si.unit_price), 0) as total_revenue
            FROM Part p
            LEFT JOIN SaleItem si ON p.part_id = si.part_id
            WHERE p.name NOT LIKE '[DEACTIVATED]%'
            GROUP BY p.part_id
            ORDER BY total_qty_sold DESC
            LIMIT ?
        """, (limit,))
        return [
            {
                "part_number": row["part_number"],
                "name": row["name"],
                "brand": row["brand"],
                "category": row["category"],
                "total_qty_sold": row["total_qty_sold"],
                "total_revenue": row["total_revenue"]
            }
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        logging.error(f"Error in get_top_selling_parts: {e}")
        return []
    finally:
        conn.close()

def get_low_stock_parts() -> List[Dict[str, Any]]:
    """
    Returns all parts where quantity_on_hand <= reorder_level.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT part_id, part_number, name, brand, category,
                   quantity_on_hand, reorder_level
            FROM Part
            WHERE quantity_on_hand <= reorder_level
              AND name NOT LIKE '[DEACTIVATED]%'
            ORDER BY quantity_on_hand ASC
        """)
        return [
            {
                "part_id": row["part_id"],
                "part_number": row["part_number"],
                "name": row["name"],
                "brand": row["brand"],
                "category": row["category"],
                "quantity_on_hand": row["quantity_on_hand"],
                "reorder_level": row["reorder_level"],
                "shortage": row["reorder_level"] - row["quantity_on_hand"]
            }
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        logging.error(f"Error in get_low_stock_parts: {e}")
        return []
    finally:
        conn.close()

def get_profit_margin_report() -> List[Dict[str, Any]]:
    """
    Returns revenue, cost-of-goods-sold and margin per part sold.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.part_number, p.name, p.brand,
                   p.cost_price, p.selling_price,
                   COALESCE(SUM(si.quantity), 0) as total_sold,
                   COALESCE(SUM(si.quantity * si.unit_price), 0) as total_revenue,
                   COALESCE(SUM(si.quantity * p.cost_price), 0) as total_cogs
            FROM Part p
            LEFT JOIN SaleItem si ON p.part_id = si.part_id
            WHERE p.name NOT LIKE '[DEACTIVATED]%'
            GROUP BY p.part_id
            ORDER BY total_revenue DESC
        """)
        results = []
        for row in cursor.fetchall():
            revenue = row["total_revenue"]
            cogs = row["total_cogs"]
            gross_profit = revenue - cogs
            margin_pct = (gross_profit / revenue * 100) if revenue > 0 else 0.0
            results.append({
                "part_number": row["part_number"],
                "name": row["name"],
                "brand": row["brand"],
                "cost_price": row["cost_price"],
                "selling_price": row["selling_price"],
                "total_sold": row["total_sold"],
                "total_revenue": revenue,
                "total_cogs": cogs,
                "gross_profit": gross_profit,
                "margin_pct": margin_pct
            })
        return results
    except sqlite3.Error as e:
        logging.error(f"Error in get_profit_margin_report: {e}")
        return []
    finally:
        conn.close()
