"""
Shared pytest fixtures. Every test gets a fresh, isolated SQLite database
file in a temp directory, so tests never touch the real motor_spares.db and
never leak state between tests.
"""

import pytest
import database.db_manager as db_manager
import utils.receipt_generator as receipt_generator


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Points the app at a fresh temp database and initializes the schema."""
    db_file = tmp_path / "test_motor_spares.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_file))

    # Also redirect receipt PDFs to a temp folder, so running the test suite
    # doesn't leave real receipt files behind in the actual project.
    receipts_dir = tmp_path / "receipts"
    monkeypatch.setattr(receipt_generator, "RECEIPTS_DIR", str(receipts_dir))

    db_manager.initialize_database()
    yield str(db_file)


@pytest.fixture
def admin_user(test_db):
    """Creates the default admin account and returns the authenticated User."""
    from managers.auth_manager import ensure_default_admin, authenticate_user
    ensure_default_admin()
    user, _ = authenticate_user("admin", "admin123")
    return user