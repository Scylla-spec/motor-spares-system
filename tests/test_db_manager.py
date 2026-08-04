"""Tests for database schema initialization (Section 5.3)."""

import sqlite3


def test_initialize_database_creates_all_tables(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    expected = {
        "User", "Customer", "Supplier", "Part", "StockMovement",
        "Sale", "SaleItem", "PurchaseOrder", "AuditLog"
    }
    assert expected.issubset(tables)


def test_initialize_database_is_idempotent(test_db):
    """Running initialization twice on the same DB should not error (migrations are safe re-runs)."""
    import database.db_manager as db_manager
    db_manager.initialize_database()
    db_manager.initialize_database()  # should not raise


def test_user_table_has_lockout_columns(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(User);")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()
    assert "failed_attempts" in columns
    assert "locked_until" in columns