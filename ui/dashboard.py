"""
Modern Dashboard and Main Window Shell for Motor Spares System.
Implements the modern ERP visual aesthetic:
- Deep slate navy sidebar (#0F172A) with warm orange pill active state (#F97316)
- Clean top header bar with user profile, role badge, and logout action
- Modern KPI metric cards, clean data tables, and seamless screen navigation
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QListWidget, QListWidgetItem,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QApplication, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from datetime import date

from models.user import User
from ui.user_management_screen import UserManagementScreen
from ui.inventory_screen import InventoryScreen
from ui.pos_screen import POSScreen
from ui.credit_screen import CreditScreen
from ui.customers_screen import CustomersScreen
from ui.suppliers_screen import SuppliersScreen
from ui.reports_screen import ReportsScreen
from ui.settings_screen import SettingsScreen
from managers.reports_manager import get_daily_sales_summary, get_low_stock_parts
from ui.theme import (
    MetricStatCard, StockBadgeDelegate, create_orange_button,
    COLOR_SIDEBAR_BG, COLOR_SIDEBAR_HOVER, COLOR_SIDEBAR_TEXT,
    COLOR_SIDEBAR_ACTIVE_BG, COLOR_SIDEBAR_ACTIVE_TEXT,
    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY
)


class ModernTopBar(QFrame):
    """Clean, focused top header bar displaying user identity and logout."""
    logout_requested = Signal()

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setFixedHeight(50)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border-bottom: 1px solid {COLOR_BORDER};
            }}
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 6, 20, 6)
        layout.setSpacing(14)

        layout.addStretch()

        # Logout Button (only thing in top bar)
        logout_btn = QPushButton("Logout")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                color: {COLOR_TEXT_SECONDARY};
                font-weight: 600;
                font-size: 12px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                color: #EF4444;
                border-color: #FECACA;
                background-color: #FEF2F2;
            }}
        """)
        logout_btn.clicked.connect(self.logout_requested.emit)
        layout.addWidget(logout_btn)


class DashboardScreen(QWidget):
    """
    Home / overview screen shown right after login.
    Displays modern KPI metric summary cards and the low-stock parts preview table.
    """
    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Welcome Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        welcome_title = QLabel(f"Welcome, {self.current_user.username}")
        welcome_title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 800;
            color: {COLOR_TEXT_PRIMARY};
        """)
        subtitle = QLabel("Here is today's overview and critical stock summary.")
        subtitle.setStyleSheet(f"""
            font-size: 12px;
            color: {COLOR_TEXT_SECONDARY};
        """)
        header_layout.addWidget(welcome_title)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)

        # Summary Metric Cards Row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        self.sales_card = MetricStatCard("Today's Sales Revenue", "$0.00")
        self.transactions_card = MetricStatCard("Today's Transactions", "0")
        self.low_stock_card = MetricStatCard("Low Stock Items", "0")

        cards_layout.addWidget(self.sales_card)
        cards_layout.addWidget(self.transactions_card)
        cards_layout.addWidget(self.low_stock_card)
        cards_layout.addStretch()
        layout.addLayout(cards_layout)

        # Low Stock Preview Section
        section_header_layout = QHBoxLayout()
        section_title = QLabel("Parts Needing Reorder")
        section_title.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 700;
            color: {COLOR_TEXT_PRIMARY};
        """)
        section_header_layout.addWidget(section_title)
        section_header_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        section_header_layout.addWidget(refresh_btn)
        layout.addLayout(section_header_layout)

        # Low Stock Table
        self.low_stock_table = QTableWidget()
        self.low_stock_table.setColumnCount(4)
        self.low_stock_table.setHorizontalHeaderLabels([
            "Part Number", "Name", "In Stock", "Reorder Level"
        ])
        self.low_stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.low_stock_table.setItemDelegateForColumn(2, StockBadgeDelegate(self.low_stock_table))
        self.low_stock_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.low_stock_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.low_stock_table.verticalHeader().setVisible(False)
        layout.addWidget(self.low_stock_table)

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
            
            stock_item = QTableWidgetItem(str(item["quantity_on_hand"]))
            stock_item.setData(Qt.UserRole + 1, True)  # mark as low stock
            self.low_stock_table.setItem(row, 2, stock_item)
            
            self.low_stock_table.setItem(row, 3, QTableWidgetItem(str(item["reorder_level"])))


class DashboardWindow(QMainWindow):
    """
    Main Application Window Shell.
    Features:
    - Deep Slate Navy Sidebar Navigation with warm orange active pill
    - Clean top header bar with user profile and logout
    - Seamless switching across application screens
    """
    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user

        self.setWindowTitle(f"Motor Spares System - {self.current_user.username} ({self.current_user.role})")
        self.resize(1200, 800)
        self.setMinimumSize(960, 640)

        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        root_layout = QHBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -------------------------------------------------------------
        # 1. Deep Navy Sidebar
        # -------------------------------------------------------------
        sidebar_frame = QFrame()
        sidebar_frame.setFixedWidth(230)
        sidebar_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_SIDEBAR_BG};
                border: none;
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(14, 20, 14, 20)
        sidebar_layout.setSpacing(12)

        # App Brand Header
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(2)
        brand_title = QLabel("Motor Spares System")
        brand_title.setStyleSheet("""
            color: #FFFFFF;
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 0.3px;
        """)
        brand_subtitle = QLabel("Administration" if self.current_user.is_admin() else "Sales Terminal")
        brand_subtitle.setStyleSheet(f"""
            color: {COLOR_SIDEBAR_TEXT};
            font-size: 12px;
            font-weight: 500;
        """)
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_subtitle)
        sidebar_layout.addLayout(brand_layout)

        sidebar_layout.addSpacing(16)

        # Navigation List Widget
        self.sidebar_list = QListWidget()
        self.sidebar_list.setFocusPolicy(Qt.NoFocus)
        self.sidebar_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                color: {COLOR_SIDEBAR_TEXT};
                font-size: 13px;
                font-weight: 600;
            }}
            QListWidget::item {{
                padding: 10px 14px;
                margin-bottom: 4px;
                border-radius: 8px;
                color: {COLOR_SIDEBAR_TEXT};
            }}
            QListWidget::item:hover {{
                background-color: {COLOR_SIDEBAR_HOVER};
                color: #FFFFFF;
            }}
            QListWidget::item:selected {{
                background-color: {COLOR_SIDEBAR_ACTIVE_BG};
                color: {COLOR_SIDEBAR_ACTIVE_TEXT};
                font-weight: 700;
            }}
        """)
        self.sidebar_list.currentRowChanged.connect(self.display_screen)
        sidebar_layout.addWidget(self.sidebar_list)

        sidebar_layout.addStretch()

        root_layout.addWidget(sidebar_frame)

        # -------------------------------------------------------------
        # 2. Main Content Canvas & Top Utility Bar
        # -------------------------------------------------------------
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top Bar
        self.top_bar = ModernTopBar(self.current_user)
        self.top_bar.logout_requested.connect(self.logout)
        content_layout.addWidget(self.top_bar)

        # Screen Stack
        self.content_area = QStackedWidget()
        content_layout.addWidget(self.content_area)

        root_layout.addWidget(content_container)

        self.setup_screens()

    def setup_screens(self):
        # 0: Dashboard Overview
        self.dashboard_screen = DashboardScreen(self.current_user)
        self.add_nav_item("Dashboard Overview", self.dashboard_screen)

        # 1: Inventory
        self.inventory_screen = InventoryScreen(self.current_user)
        self.add_nav_item("Inventory", self.inventory_screen)

        # 2: Point of Sale
        self.pos_screen = POSScreen(self.current_user)
        self.add_nav_item("Point of Sale", self.pos_screen)

        # 3: Pay Later / On Credit
        self.credit_screen = CreditScreen(self.current_user)
        self.add_nav_item("Pay Later / On Credit", self.credit_screen)

        # 4: Customers
        self.customers_screen = CustomersScreen(self.current_user)
        self.add_nav_item("Customers", self.customers_screen)

        # 5: Suppliers
        self.suppliers_screen = SuppliersScreen(self.current_user)
        self.add_nav_item("Suppliers", self.suppliers_screen)

        # 6: Reports
        self.reports_screen = ReportsScreen(self.current_user)
        self.add_nav_item("Reports", self.reports_screen)

        # 7: User Management (Admin Only)
        if self.current_user.is_admin():
            self.user_mgmt_screen = UserManagementScreen()
            self.add_nav_item("User Management", self.user_mgmt_screen)

        # 8: Settings Screen (Admin Only)
        if self.current_user.is_admin():
            self.settings_screen = SettingsScreen()
            self.add_nav_item("Settings", self.settings_screen)

        self.sidebar_list.setCurrentRow(0)

    def add_nav_item(self, label_text, widget):
        item = QListWidgetItem(label_text)
        self.sidebar_list.addItem(item)
        self.content_area.addWidget(widget)

    def display_screen(self, index):
        if index >= 0 and index < self.content_area.count():
            self.content_area.setCurrentIndex(index)
            if index == 0:
                self.dashboard_screen.refresh()
            elif index == 3 and hasattr(self, 'credit_screen'):
                self.credit_screen.refresh()

    def navigate_to_settings(self):
        if self.settings_screen_index is not None:
            self.sidebar_list.clearSelection()
            self.content_area.setCurrentIndex(self.settings_screen_index)

    def navigate_to_pos(self):
        # Index 2 is Point of Sale
        self.sidebar_list.setCurrentRow(2)

    def logout(self):
        reply = QMessageBox.question(
            self, "Confirm Logout", "Are you sure you want to log out?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()
            # Launch fresh login window
            from ui.login_window import LoginWindow
            self._new_login = LoginWindow()
            def on_relogin(user):
                self._new_dash = DashboardWindow(current_user=user)
                self._new_dash.show()
            self._new_login.login_successful.connect(on_relogin)
            self._new_login.show()