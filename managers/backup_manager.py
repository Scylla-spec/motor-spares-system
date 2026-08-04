"""
FR-13: Owner/Admin can back up the database to a local file.

Copies the live SQLite database file to a timestamped backup, so it can't
be silently overwritten by a second backup taken the same day.
"""

import shutil
import os
import logging
from datetime import datetime
from database.db_manager import DB_PATH

BACKUP_DIR = "backups"


def backup_database() -> tuple[bool, str]:
    """
    Copies the live database file to backups/motor_spares_YYYYMMDD_HHMMSS.db.
    Returns (success, message_or_path).
    """
    if not os.path.exists(DB_PATH):
        return False, "Database file not found -- nothing to back up."

    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"motor_spares_{timestamp}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        shutil.copy2(DB_PATH, backup_path)

        logging.info(f"Database backed up to {backup_path}")
        return True, backup_path
    except OSError as e:
        logging.error(f"Backup failed: {e}")
        return False, f"Backup failed: {e}"


def list_backups() -> list[str]:
    """Returns backup filenames in backups/, most recent first."""
    if not os.path.exists(BACKUP_DIR):
        return []
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")]
    files.sort(reverse=True)
    return files