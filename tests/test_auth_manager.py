"""
Tests for managers/auth_manager.py: password hashing and account lockout
(NFR-05, error handling Section 3.7).
"""

from managers.auth_manager import (
    hash_password, verify_password, ensure_default_admin,
    authenticate_user, create_user, MAX_FAILED_ATTEMPTS
)


def test_password_hash_is_salted_and_verifiable(test_db):
    hashed = hash_password("mypassword123")
    assert verify_password(hashed, "mypassword123") is True
    assert verify_password(hashed, "wrongpassword") is False


def test_two_hashes_of_same_password_differ(test_db):
    h1 = hash_password("samepassword")
    h2 = hash_password("samepassword")
    assert h1 != h2


def test_successful_login(test_db):
    ensure_default_admin()
    user, message = authenticate_user("admin", "admin123")
    assert user is not None
    assert user.username == "admin"
    assert message == ""


def test_wrong_password_does_not_authenticate(test_db):
    ensure_default_admin()
    user, message = authenticate_user("admin", "wrongpassword")
    assert user is None
    assert "invalid" in message.lower()


def test_unknown_username_does_not_authenticate(test_db):
    ensure_default_admin()
    user, message = authenticate_user("nosuchuser", "whatever")
    assert user is None


def test_account_locks_after_max_failed_attempts(test_db):
    ensure_default_admin()

    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        user, message = authenticate_user("admin", "wrongpassword")
        assert user is None

    user, message = authenticate_user("admin", "wrongpassword")
    assert user is None
    assert "locked" in message.lower()

    user, message = authenticate_user("admin", "admin123")
    assert user is None
    assert "locked" in message.lower()


def test_successful_login_resets_failed_attempts(test_db):
    ensure_default_admin()
    authenticate_user("admin", "wrongpassword")
    authenticate_user("admin", "wrongpassword")

    user, message = authenticate_user("admin", "admin123")
    assert user is not None

    from database.db_manager import get_connection
    conn = get_connection()
    row = conn.execute("SELECT failed_attempts FROM User WHERE username='admin'").fetchone()
    conn.close()
    assert row["failed_attempts"] == 0


def test_create_user_rejects_duplicate_username(test_db):
    assert create_user("mtha", "password123", "Cashier") is True
    assert create_user("mtha", "differentpassword", "Cashier") is False