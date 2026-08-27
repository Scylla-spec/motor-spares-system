import sqlite3
import logging
import os

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

DB_PATH = os.path.join("database", "motor_spares.db")


def get_connection():
    """Establishes and returns a database connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def initialize_database():
    """Creates all required tables, constraints, and indexes for the system."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. User Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS User (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT CHECK(role IN ('Cashier', 'Admin')) NOT NULL
            );
        """)

        # 2. Customer Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Customer (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                credit_balance REAL DEFAULT 0.0
            );
        """)

        # 3. Supplier Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Supplier (
                supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact_phone TEXT,
                address TEXT
            );
        """)

        # 4. Part Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Part (
                part_id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_number TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                brand TEXT,
                compatible_vehicles TEXT,
                quantity_on_hand INTEGER NOT NULL DEFAULT 0 CHECK(quantity_on_hand >= 0),
                cost_price REAL NOT NULL CHECK(cost_price >= 0),
                selling_price REAL NOT NULL CHECK(selling_price >= 0),
                reorder_level INTEGER DEFAULT 0,
                supplier_id INTEGER,
                FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id) ON DELETE RESTRICT
            );
        """)

        # Search Indexes for Part
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_part_category ON Part(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_part_brand ON Part(brand);")

        # 5. StockMovement Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS StockMovement (
                movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id INTEGER NOT NULL,
                movement_type TEXT CHECK(movement_type IN ('IN', 'OUT')) NOT NULL,
                quantity INTEGER NOT NULL,
                reason TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (part_id) REFERENCES Part(part_id) ON DELETE RESTRICT
            );
        """)

        # 6. Sale Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Sale (
                sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                total_amount REAL NOT NULL,
                payment_method TEXT CHECK(payment_method IN ('Cash', 'EcoCash', 'Card')) NOT NULL,
                timestamp TEXT NOT NULL,
                cashier_id INTEGER NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE SET NULL,
                FOREIGN KEY (cashier_id) REFERENCES User(user_id) ON DELETE RESTRICT
            );
        """)

        # 7. SaleItem Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SaleItem (
                sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                unit_price REAL NOT NULL,
                FOREIGN KEY (sale_id) REFERENCES Sale(sale_id) ON DELETE CASCADE,
                FOREIGN KEY (part_id) REFERENCES Part(part_id) ON DELETE RESTRICT
            );
        """)

        # 8. PurchaseOrder Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS PurchaseOrder (
                po_id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                status TEXT CHECK(status IN ('Draft', 'Ordered', 'Received')) NOT NULL,
                order_date TEXT,
                total_cost REAL,
                FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id) ON DELETE RESTRICT
            );
        """)

        # 9. AuditLog Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AuditLog (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT CHECK(action IN ('ADJUSTMENT', 'PRICE_CHANGE', 'DEACTIVATE')) NOT NULL,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                old_value TEXT,
                new_value TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE RESTRICT
            );
        """)

        # Lookup Index for AuditLog
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_lookup ON AuditLog(table_name, record_id);")

        # 10. ShopSettings Table (FR-18) — simple key/value config store
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ShopSettings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT
            );
        """)

        # 11. ReorderWishlist Table (FR-21) — manually-added reorder items
        # for parts that are unavailable or not yet catalogued.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ReorderWishlist (
                wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                preferred_supplier_id INTEGER,
                priority TEXT NOT NULL CHECK(priority IN ('High', 'Medium', 'Low')) DEFAULT 'Medium',
                notes TEXT,
                date_added TEXT NOT NULL,
                added_by INTEGER,
                FOREIGN KEY (preferred_supplier_id) REFERENCES Supplier(supplier_id) ON DELETE SET NULL,
                FOREIGN KEY (added_by) REFERENCES User(user_id) ON DELETE SET NULL
            );
        """)

        # 12. CreditOrder Table — goods given to customers on credit (pay later)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS CreditOrder (
                credit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                customer_name TEXT NOT NULL,
                customer_phone TEXT,
                total_amount REAL NOT NULL CHECK(total_amount >= 0),
                amount_paid REAL NOT NULL DEFAULT 0.0,
                status TEXT CHECK(status IN ('Pending', 'Paid')) NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL,
                due_date TEXT,
                paid_at TEXT,
                cashier_id INTEGER,
                notes TEXT,
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE SET NULL,
                FOREIGN KEY (cashier_id) REFERENCES User(user_id) ON DELETE SET NULL
            );
        """)

        # 13. CreditOrderItem Table — items associated with a credit order
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS CreditOrderItem (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                credit_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                part_number TEXT,
                part_name TEXT,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                unit_price REAL NOT NULL,
                FOREIGN KEY (credit_id) REFERENCES CreditOrder(credit_id) ON DELETE CASCADE,
                FOREIGN KEY (part_id) REFERENCES Part(part_id) ON DELETE RESTRICT
            );
        """)

        # Seed default branding values on first run only (won't overwrite
        # values an Admin has already changed via the Settings screen).
        default_settings = {
            "shop_name": "Motor Spares Management",
            "address": "123 Auto Lane, Bulawayo, Zimbabwe",
            "phone": "+263 77 123 4567",
            "receipt_footer": "Thank you for your business!",
            "logo_path": "",
        }
        for key, value in default_settings.items():
            cursor.execute(
                "INSERT OR IGNORE INTO ShopSettings (setting_key, setting_value) VALUES (?, ?);",
                (key, value)
            )

        # --- Migration: add account-lockout columns to User if they don't exist yet ---
        # (Safe to re-run: checks first, so it won't error on a fresh DB that
        # already has them, or a pre-existing DB that doesn't.)
        cursor.execute("PRAGMA table_info(User);")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "failed_attempts" not in existing_columns:
            cursor.execute("ALTER TABLE User ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0;")
        if "locked_until" not in existing_columns:
            cursor.execute("ALTER TABLE User ADD COLUMN locked_until TEXT;")

        # --- Migration: add po_number to PurchaseOrder if missing ---
        cursor.execute("PRAGMA table_info(PurchaseOrder);")
        po_columns = {row[1] for row in cursor.fetchall()}
        if "po_number" not in po_columns:
            cursor.execute("ALTER TABLE PurchaseOrder ADD COLUMN po_number TEXT;")

        conn.commit()
        logging.info("Database schema initialized successfully.")
        print("Database schema initialized successfully.")

    except sqlite3.Error as e:
        logging.error(f"Database initialization failed: {e}")
        print(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    initialize_database()