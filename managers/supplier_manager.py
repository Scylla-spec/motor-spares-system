import sqlite3
import logging
from typing import List
from database.db_manager import get_connection
from models.supplier import Supplier

def add_supplier(supplier: Supplier) -> bool:
    """Adds a new supplier."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Supplier (name, contact_phone, address)
            VALUES (?, ?, ?)
        """, (supplier.name, supplier.contact_phone, supplier.address))
        conn.commit()
        supplier.supplier_id = cursor.lastrowid
        logging.info(f"Supplier '{supplier.name}' added successfully.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error adding supplier: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_supplier(supplier: Supplier) -> bool:
    """Updates an existing supplier."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Supplier SET name = ?, contact_phone = ?, address = ?
            WHERE supplier_id = ?
        """, (supplier.name, supplier.contact_phone, supplier.address, supplier.supplier_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error updating supplier: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_suppliers() -> List[Supplier]:
    """Retrieves all suppliers."""
    conn = get_connection()
    cursor = conn.cursor()
    suppliers = []
    try:
        cursor.execute("SELECT * FROM Supplier;")
        for row in cursor.fetchall():
            suppliers.append(Supplier(
                supplier_id=row["supplier_id"],
                name=row["name"],
                contact_phone=row["contact_phone"],
                address=row["address"]
            ))
        return suppliers
    except sqlite3.Error as e:
        logging.error(f"Database error fetching suppliers: {e}")
        return []
    finally:
        conn.close()


def delete_supplier(supplier_id: int) -> bool:
    """Deletes a supplier."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Supplier WHERE supplier_id = ?;", (supplier_id,))
        conn.commit()
        logging.info(f"Supplier ID {supplier_id} deleted successfully.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error deleting supplier: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
