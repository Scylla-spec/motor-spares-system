import sqlite3
import logging
from typing import Dict
from database.db_manager import get_connection

# Fallback defaults, used only if a key is somehow missing from the table
# (e.g. a DB created before this feature existed and not yet migrated).
DEFAULTS = {
    "shop_name": "Motor Spares Management",
    "address": "123 Auto Lane, Bulawayo, Zimbabwe",
    "phone": "+263 77 123 4567",
    "receipt_footer": "Thank you for your business!",
    "logo_path": "",
}


def get_all_settings() -> Dict[str, str]:
    """Returns all shop settings as a dict, falling back to DEFAULTS for any
    key not present in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    settings = dict(DEFAULTS)
    try:
        cursor.execute("SELECT setting_key, setting_value FROM ShopSettings;")
        for row in cursor.fetchall():
            settings[row["setting_key"]] = row["setting_value"] or ""
        return settings
    except sqlite3.Error as e:
        logging.error(f"Database error fetching settings: {e}")
        return settings
    finally:
        conn.close()


def get_setting(key: str) -> str:
    """Returns a single setting value, falling back to its default."""
    return get_all_settings().get(key, DEFAULTS.get(key, ""))


def update_settings(values: Dict[str, str]) -> bool:
    """Updates one or more settings. Only keys present in `values` are
    touched; everything else is left as-is."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for key, value in values.items():
            cursor.execute("""
                INSERT INTO ShopSettings (setting_key, setting_value)
                VALUES (?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value;
            """, (key, value))
        conn.commit()
        logging.info(f"Shop settings updated: {list(values.keys())}")
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error updating settings: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
