from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QListWidget, QListWidgetItem,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from datetime import date
from models.user import User
from ui.user_management_screen import UserManagementScreen
from ui.inventory_screen import InventoryScreen
from ui.pos_screen import POSScreen
from ui.customers_screen import CustomersScreen
from ui.suppliers_screen import SuppliersScreen
from ui.reports_screen import ReportsScreen
from managers.reports_manager import get_daily_sales_summary, get_low_stock_parts


class PlaceholderScreen(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel(f"<h2>{title} Screen</h2><p>This module is not yet implemented.</p>")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)


class SummaryCard(QFrame):
    """A single stat card, e.g. Today's Sales: $240.00"""
    def __init__(self, title: str, value: str, color: str = "#2c3e50", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
                padding: 10px;
            }}
            QLabel {{ color: white; background: transparent; }}
        """)
        self.setMinimumHeight(100)
        layout = QVBoxLayout(self)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("font-size: 26px; font-weight: bold;")
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class DashboardScreen(QWidget):
    """
    Home / overview screen shown right after login (Section 5.5 of the docs).
    Shows today's sales, low-stock count, and a quick low-stock list so the
    owner/cashier gets a useful snapshot before navigating anywhere else.
    """
    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel(f"<h2>Welcome, {self.current_user.username}</h2>"))

        # --- Summary cards row ---
        cards_layout = QHBoxLayout()
        self.sales_card = SummaryCard("Today's Sales Revenue", "$0.00", color="#27ae60")
        self.transactions_card = SummaryCard("Today's Transactions", "0", color="#2980b9")
        self.low_stock_card = SummaryCard("Low Stock Items", "0", color="#c0392b")

        cards_layout.addWidget(self.sales_card)
        cards_layout.addWidget(self.transactions_card)
        cards_layout.addWidget(self.low_stock_card)
        layout.addLayout(cards_layout)

        # --- Low stock preview table ---
        layout.addWidget(QLabel("<h3>Parts Needing Reorder</h3>"))
        self.low_stock_table = QTableWidget()
        self.low_stock_table.setColumnCount(4)
        self.low_stock_table.setHorizontalHeaderLabels(
            ["Part Number", "Name", "In Stock", "Reorder Level"]
        )
        self.low_stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.low_stock_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.low_stock_table)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

    def refresh(self):
        today_str = date.today().isoformat()
        summary = get_daily_sales_summary(today_str)
        self.sales_card.set_value(f"${summary['total_revenue']:.2f}")
        self.transactions_card.set_value(str(summary['transaction_count']))

        low_stock = get_low_stock_parts()
        self.low_stock_card.set_value(str(len(low_stock)))

        self.low_stock_table.setRowCount(len(low_stock))
        for row, item in enumerate(low_stock):
            self.low_stock_table.setItem(row, 0, QTableWidgetItem(item["part_number"]))
            self.low_stock_table.setItem(row, 1, QTableWidgetItem(item["name"]))
            self.low_stock_table.setItem(row, 2, QTableWidgetItem(str(item["quantity_on_hand"])))
            self.low_stock_table.setItem(row, 3, QTableWidgetItem(str(item["reorder_level"])))


class DashboardWindow(QMainWindow):
    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        
        self.setWindowTitle(f"Motor Spares System - Logged in as {self.current_user.username} ({self.current_user.role})")
        self.resize(1024, 768)
        
        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar Navigation
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.currentRowChanged.connect(self.display_screen)
        
        # Add basic style to sidebar
        self.sidebar.setStyleSheet("""
            QListWidget { background-color: #2c3e50; color: white; font-size: 14px; }
            QListWidget::item { padding: 15px; border-bottom: 1px solid #34495e; }
            QListWidget::item:selected { background-color: #3498db; }
        """)
        
        layout.addWidget(self.sidebar)
        
        # Main Content Area
        self.content_area = QStackedWidget()
        layout.addWidget(self.content_area)
        
        self.setup_screens()

    def setup_screens(self):
        # 0: Home / Overview
        self.dashboard_screen = DashboardScreen(self.current_user)
        self.add_nav_item("Dashboard Overview", self.dashboard_screen)
        
        # 1: Inventory
        self.add_nav_item("Inventory", InventoryScreen(self.current_user))
        
        # 2: POS / Sales
        self.add_nav_item("Point of Sale", POSScreen(self.current_user))
        
        # 3: Customers
        self.add_nav_item("Customers", CustomersScreen(self.current_user))
        
        # 4: Suppliers
        self.add_nav_item("Suppliers", SuppliersScreen(self.current_user))
        
        # 5: Reports
        self.add_nav_item("Reports", ReportsScreen(self.current_user))
        
        # 6: User Management (Admin Only)
        if self.current_user.is_admin():
            self.add_nav_item("User Management", UserManagementScreen())
            
        self.sidebar.setCurrentRow(0)

    def add_nav_item(self, label_text, widget):
        item = QListWidgetItem(label_text)
        self.sidebar.addItem(item)
        self.content_area.addWidget(widget)

    def display_screen(self, index):
        self.content_area.setCurrentIndex(index)
        if index == 0:
            self.dashboard_screen.refresh()