import hashlib
import os
import sqlite3
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from database.db_manager import get_connection
from models.user import User

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 5


def hash_password(password: str, salt: bytes = None) -> str:
    """Hashes a password using SHA-256 with a salt. Returns salt$hash."""
    if salt is None:
        salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}${hashed.hex()}"


def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    """Verifies a provided password against a stored salt$hash string."""
    try:
        salt_hex, hash_hex = stored_password_hash.split('$')
        salt = bytes.fromhex(salt_hex)
        recalculated_hash = hash_password(provided_password, salt).split('$')[1]
        return recalculated_hash == hash_hex
    except Exception as e:
        logging.error(f"Error verifying password: {e}")
        return False


def ensure_default_admin():
    """Seeds a default admin user (admin / admin123) if no users exist in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM User;")
        count = cursor.fetchone()[0]
        if count == 0:
            default_username = "admin"
            default_password = "admin123"  # Prompt change on first run in production
            password_hash = hash_password(default_password)
            cursor.execute(
                "INSERT INTO User (username, password_hash, role) VALUES (?, ?, ?);",
                (default_username, password_hash, "Admin")
            )
            conn.commit()
            logging.info("Default Admin account created (admin/admin123).")
            print("Default Admin account created (Username: admin, Password: admin123).")
    except sqlite3.Error as e:
        logging.error(f"Failed to seed default admin: {e}")
        conn.rollback()
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Tuple[Optional[User], str]:
    """
    Authenticates a user against the database.

    Enforces account lockout after MAX_FAILED_ATTEMPTS consecutive failures:
    the account is locked for LOCKOUT_MINUTES, during which login is rejected
    even with the correct password.

    Returns (User_or_None, message). message is empty on success, otherwise
    explains why login failed (wrong credentials vs. locked out) so the UI
    can show something more useful than a generic error.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT user_id, username, password_hash, role, failed_attempts, locked_until "
            "FROM User WHERE username = ?;",
            (username,)
        )
        row = cursor.fetchone()

        if not row:
            # Don't reveal whether the username exists.
            logging.warning(f"Failed login attempt for unknown username '{username}'.")
            return None, "Invalid username or password."

        # Check for an active lockout first.
        if row["locked_until"]:
            locked_until = datetime.fromisoformat(row["locked_until"])
            if datetime.now() < locked_until:
                remaining = int((locked_until - datetime.now()).total_seconds() / 60) + 1
                logging.warning(f"Login attempt on locked account '{username}'.")
                return None, f"Account locked due to repeated failed logins. Try again in {remaining} minute(s)."

        if verify_password(row["password_hash"], password):
            # Successful login: clear any failed-attempt counter/lockout.
            cursor.execute(
                "UPDATE User SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?;",
                (row["user_id"],)
            )
            conn.commit()

            user = User(
                user_id=row["user_id"],
                username=row["username"],
                password_hash=row["password_hash"],
                role=row["role"]
            )
            logging.info(f"User '{username}' logged in successfully.")
            return user, ""

        # Wrong password: increment the counter, lock the account if the limit is hit.
        new_attempts = row["failed_attempts"] + 1
        if new_attempts >= MAX_FAILED_ATTEMPTS:
            locked_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            cursor.execute(
                "UPDATE User SET failed_attempts = 0, locked_until = ? WHERE user_id = ?;",
                (locked_until, row["user_id"])
            )
            conn.commit()
            logging.warning(f"Account '{username}' locked after {MAX_FAILED_ATTEMPTS} failed attempts.")
            return None, f"Too many failed attempts. Account locked for {LOCKOUT_MINUTES} minutes."
        else:
            cursor.execute(
                "UPDATE User SET failed_attempts = ? WHERE user_id = ?;",
                (new_attempts, row["user_id"])
            )
            conn.commit()
            remaining_tries = MAX_FAILED_ATTEMPTS - new_attempts
            logging.warning(f"Failed login attempt for username '{username}' ({new_attempts}/{MAX_FAILED_ATTEMPTS}).")
            return None, f"Invalid username or password. {remaining_tries} attempt(s) remaining before lockout."

    except sqlite3.Error as e:
        logging.error(f"Database error during authentication: {e}")
        return None, "A database error occurred. Please try again."
    finally:
        conn.close()


def create_user(username: str, password: str, role: str) -> bool:
    """Creates a new user account (Admin only action)."""
    if role not in ('Cashier', 'Admin'):
        logging.error(f"Invalid role attempted: {role}")
        return False

    password_hash = hash_password(password)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO User (username, password_hash, role) VALUES (?, ?, ?);",
            (username, password_hash, role)
        )
        conn.commit()
        logging.info(f"User '{username}' with role '{role}' created.")
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"Attempted to create duplicate username: '{username}'.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Failed to create user: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_all_users() -> list[User]:
    """Retrieves all users from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    users = []
    try:
        cursor.execute("SELECT user_id, username, password_hash, role FROM User;")
        for row in cursor.fetchall():
            users.append(User(
                user_id=row["user_id"],
                username=row["username"],
                password_hash=row["password_hash"],
                role=row["role"]
            ))
        return users
    except sqlite3.Error as e:
        logging.error(f"Database error fetching users: {e}")
        return []
    finally:
        conn.close()


if __name__ == "__main__":
    ensure_default_admin()
    # Test authentication
    user, message = authenticate_user("admin", "admin123")
    if user:
        print(f"Authentication success! Authenticated: {user}")
    else:
        print(f"Authentication failed: {message}")