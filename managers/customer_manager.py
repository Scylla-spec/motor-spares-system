import sqlite3
import logging
from typing import List, Dict, Any
from database.db_manager import get_connection
from models.customer import Customer
from models.sale import Sale

def add_customer(customer: Customer) -> bool:
    """Adds a new customer."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Customer (name, phone, credit_balance)
            VALUES (?, ?, ?)
        """, (customer.name, customer.phone, customer.credit_balance))
        conn.commit()
        customer.customer_id = cursor.lastrowid
        logging.info(f"Customer '{customer.name}' added successfully.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error adding customer: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_customer(customer: Customer) -> bool:
    """Updates an existing customer."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Customer SET name = ?, phone = ?, credit_balance = ?
            WHERE customer_id = ?
        """, (customer.name, customer.phone, customer.credit_balance, customer.customer_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error updating customer: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_customers() -> List[Customer]:
    """Retrieves all customers."""
    conn = get_connection()
    cursor = conn.cursor()
    customers = []
    try:
        cursor.execute("SELECT * FROM Customer;")
        for row in cursor.fetchall():
            customers.append(Customer(
                customer_id=row["customer_id"],
                name=row["name"],
                phone=row["phone"],
                credit_balance=row["credit_balance"]
            ))
        return customers
    except sqlite3.Error as e:
        logging.error(f"Database error fetching customers: {e}")
        return []
    finally:
        conn.close()

def get_customer_purchase_history(customer_id: int) -> List[Dict[str, Any]]:
    """Retrieves a list of basic sale info for a specific customer."""
    conn = get_connection()
    cursor = conn.cursor()
    history = []
    try:
        cursor.execute("""
            SELECT sale_id, total_amount, payment_method, timestamp 
            FROM Sale 
            WHERE customer_id = ? 
            ORDER BY timestamp DESC
        """, (customer_id,))
        for row in cursor.fetchall():
            history.append({
                "sale_id": row["sale_id"],
                "total_amount": row["total_amount"],
                "payment_method": row["payment_method"],
                "timestamp": row["timestamp"]
            })
        return history
    except sqlite3.Error as e:
        logging.error(f"Database error fetching customer history: {e}")
        return []
    finally:
        conn.close()
