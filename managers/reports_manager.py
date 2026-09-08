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


# --- Retail Health & Root-Cause Diagnostic Matrix (NuClass-Inspired) ---

def get_dead_capital_matrix(days_threshold: int = 90) -> Dict[str, Any]:
    """
    Identifies parts where capital is frozen (stock on hand > 0 with no sales
    recorded in the last `days_threshold` days).
    Returns category breakdown, total tied-up capital, and individual stagnant items.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.part_id, p.part_number, p.name, p.category, p.brand,
                   p.quantity_on_hand, p.cost_price, p.selling_price,
                   (p.quantity_on_hand * p.cost_price) as tied_up_cost,
                   MAX(s.timestamp) as last_sold_date
            FROM Part p
            LEFT JOIN SaleItem si ON p.part_id = si.part_id
            LEFT JOIN Sale s ON si.sale_id = s.sale_id
            WHERE p.quantity_on_hand > 0
              AND p.name NOT LIKE '[DEACTIVATED]%'
            GROUP BY p.part_id
            HAVING last_sold_date IS NULL
                OR julianday('now') - julianday(last_sold_date) >= ?
            ORDER BY tied_up_cost DESC
        """, (days_threshold,))

        rows = cursor.fetchall()
        stagnant_parts = []
        category_summary = {}
        total_frozen_capital = 0.0

        for r in rows:
            tied_cost = float(r["tied_up_cost"] or 0.0)
            total_frozen_capital += tied_cost
            cat = r["category"] or "Uncategorized"

            if cat not in category_summary:
                category_summary[cat] = {
                    "category": cat,
                    "part_count": 0,
                    "total_units": 0,
                    "tied_up_capital": 0.0
                }
            category_summary[cat]["part_count"] += 1
            category_summary[cat]["total_units"] += r["quantity_on_hand"]
            category_summary[cat]["tied_up_capital"] += tied_cost

            stagnant_parts.append({
                "part_id": r["part_id"],
                "part_number": r["part_number"],
                "name": r["name"],
                "category": cat,
                "brand": r["brand"],
                "quantity": r["quantity_on_hand"],
                "cost_price": r["cost_price"],
                "tied_up_cost": tied_cost,
                "last_sold": (r["last_sold_date"][:10] if r["last_sold_date"] else "Never Sold")
            })

        return {
            "total_frozen_capital": total_frozen_capital,
            "stagnant_part_count": len(stagnant_parts),
            "category_breakdown": sorted(category_summary.values(), key=lambda x: x["tied_up_capital"], reverse=True),
            "stagnant_parts": stagnant_parts[:50]
        }
    except sqlite3.Error as e:
        logging.error(f"Error in get_dead_capital_matrix: {e}")
        return {"total_frozen_capital": 0.0, "stagnant_part_count": 0, "category_breakdown": [], "stagnant_parts": []}
    finally:
        conn.close()


def get_credit_risk_matrix() -> Dict[str, Any]:
    """
    Categorizes all pending credit debt into aging default risk bands:
    - 0 to 30 days: Low Risk (Current)
    - 31 to 60 days: Medium Risk (Overdue Watchlist)
    - 61 to 90 days: High Risk (Significant Default Hazard)
    - > 90 days: Critical (Default Danger / Bad Debt)
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT co.credit_id, co.customer_name, co.customer_phone,
                   co.total_amount, co.created_at, co.due_date,
                   CAST(julianday('now') - julianday(co.created_at) AS INT) as days_open
            FROM CreditOrder co
            WHERE co.status = 'Pending'
            ORDER BY days_open DESC
        """)

        bands = {
            "CURRENT": {"label": "Current (0–30 Days)", "color": "#16A34A", "count": 0, "amount": 0.0, "orders": []},
            "WATCHLIST": {"label": "Overdue (31–60 Days)", "color": "#EAB308", "count": 0, "amount": 0.0, "orders": []},
            "HIGH_RISK": {"label": "High Risk (61–90 Days)", "color": "#F97316", "count": 0, "amount": 0.0, "orders": []},
            "DEFAULT_DANGER": {"label": "Default Danger (>90 Days)", "color": "#DC2626", "count": 0, "amount": 0.0, "orders": []},
        }

        total_pending_debt = 0.0

        for row in cursor.fetchall():
            days = row["days_open"] or 0
            amt = float(row["total_amount"])
            total_pending_debt += amt

            order_data = {
                "credit_id": row["credit_id"],
                "customer_name": row["customer_name"],
                "phone": row["customer_phone"] or "—",
                "amount": amt,
                "days_open": days,
                "date_taken": row["created_at"][:10],
                "due_date": row["due_date"] or "—"
            }

            if days <= 30:
                band_key = "CURRENT"
            elif days <= 60:
                band_key = "WATCHLIST"
            elif days <= 90:
                band_key = "HIGH_RISK"
            else:
                band_key = "DEFAULT_DANGER"

            bands[band_key]["count"] += 1
            bands[band_key]["amount"] += amt
            bands[band_key]["orders"].append(order_data)

        return {
            "total_pending_debt": total_pending_debt,
            "bands": bands
        }
    except sqlite3.Error as e:
        logging.error(f"Error in get_credit_risk_matrix: {e}")
        return {"total_pending_debt": 0.0, "bands": {}}
    finally:
        conn.close()


def get_stockout_friction_matrix() -> List[Dict[str, Any]]:
    """
    Identifies parts with zero on-hand stock that have previous sales history
    or high reorder thresholds, indicating ongoing lost retail revenue.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.part_id, p.part_number, p.name, p.brand, p.category,
                   p.reorder_level, p.selling_price,
                   COALESCE(SUM(si.quantity), 0) as past_units_sold,
                   (p.reorder_level * p.selling_price) as estimated_lost_sale_exposure
            FROM Part p
            LEFT JOIN SaleItem si ON p.part_id = si.part_id
            WHERE p.quantity_on_hand = 0
              AND p.name NOT LIKE '[DEACTIVATED]%'
            GROUP BY p.part_id
            ORDER BY past_units_sold DESC, estimated_lost_sale_exposure DESC
            LIMIT 40
        """)
        return [
            {
                "part_number": r["part_number"],
                "name": r["name"],
                "brand": r["brand"],
                "category": r["category"],
                "reorder_level": r["reorder_level"],
                "selling_price": r["selling_price"],
                "past_units_sold": r["past_units_sold"],
                "lost_sale_exposure": float(r["estimated_lost_sale_exposure"] or 0.0)
            }
            for r in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        logging.error(f"Error in get_stockout_friction_matrix: {e}")
        return []
    finally:
        conn.close()

