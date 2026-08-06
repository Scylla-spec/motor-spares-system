import sqlite3
import logging
from datetime import datetime
from typing import List, Optional
from database.db_manager import get_connection
from models.wishlist_item import WishlistItem, PRIORITY_LEVELS

# Sort order so High-priority items always list before Medium before Low
_PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def add_wishlist_item(item: WishlistItem, added_by: int) -> bool:
    """Adds a new reorder wishlist entry (FR-21)."""
    if item.priority not in PRIORITY_LEVELS:
        item.priority = "Medium"

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO ReorderWishlist (
                description, preferred_supplier_id, priority, notes, date_added, added_by
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            item.description.strip(), item.preferred_supplier_id, item.priority,
            item.notes, datetime.now().isoformat(sep=' ', timespec='seconds'), added_by
        ))
        conn.commit()
        item.wishlist_id = cursor.lastrowid
        logging.info(f"Wishlist item '{item.description}' added (priority={item.priority}).")
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error adding wishlist item: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def update_wishlist_item(item: WishlistItem) -> bool:
    """Updates an existing wishlist entry (e.g. changing priority or notes)."""
    if item.priority not in PRIORITY_LEVELS:
        item.priority = "Medium"

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE ReorderWishlist
            SET description = ?, preferred_supplier_id = ?, priority = ?, notes = ?
            WHERE wishlist_id = ?
        """, (
            item.description.strip(), item.preferred_supplier_id, item.priority,
            item.notes, item.wishlist_id
        ))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error updating wishlist item: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def remove_wishlist_item(wishlist_id: int) -> bool:
    """Removes a wishlist entry \u2014 e.g. once the item has arrived and been
    promoted to a full Part record, or it's no longer needed."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ReorderWishlist WHERE wishlist_id = ?", (wishlist_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error removing wishlist item: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_all_wishlist_items() -> List[dict]:
    """Returns all wishlist items, High priority first, then Medium, then
    Low (and newest-first within the same priority). Includes the
    preferred supplier's name (if set) via a join, for display/export.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT w.wishlist_id, w.description, w.preferred_supplier_id,
                   s.name AS supplier_name, w.priority, w.notes, w.date_added
            FROM ReorderWishlist w
            LEFT JOIN Supplier s ON w.preferred_supplier_id = s.supplier_id
            ORDER BY w.date_added DESC
        """)
        rows = [dict(row) for row in cursor.fetchall()]
        rows.sort(key=lambda r: _PRIORITY_ORDER.get(r["priority"], 1))
        return rows
    except sqlite3.Error as e:
        logging.error(f"Database error fetching wishlist items: {e}")
        return []
    finally:
        conn.close()
