import sqlite3
import logging
from typing import List, Dict, Any
from database.db_manager import get_connection

def get_daily_sales_summary(date_str: str) -> Dict[str, Any]:
    """
    Returns summary for a specific date (YYYY-MM-DD).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) as transaction_count,
                   COALESCE(SUM(total_amount), 0) as total_revenue
            FROM Sale
            WHERE date(timestamp) = ?
        """, (date_str,))
        row = cursor.fetchone()
        return {
            "date": date_str,
            "transaction_count": row["transaction_count"],
            "total_revenue": row["total_revenue"]
        }
    except sqlite3.Error as e:
        logging.error(f"Error in get_daily_sales_summary: {e}")
        return {"date": date_str, "transaction_count": 0, "total_revenue": 0.0}
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
                   COALESCE(SUM(total_amount), 0) as total_revenue
            FROM Sale
            WHERE strftime('%Y-%m', timestamp) = ?
            GROUP BY sale_date
            ORDER BY sale_date
        """, (month_str,))
        return [
            {
                "date": row["sale_date"],
                "transaction_count": row["transaction_count"],
                "total_revenue": row["total_revenue"]
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
