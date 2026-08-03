from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QStackedWidget, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from models.user import User
from ui.user_management_screen import UserManagementScreen
from ui.inventory_screen import InventoryScreen
from ui.pos_screen import POSScreen
from ui.customers_screen import CustomersScreen
from ui.suppliers_screen import SuppliersScreen
from ui.reports_screen import ReportsScreen

class PlaceholderScreen(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel(f"<h2>{title} Screen</h2><p>This module is not yet implemented.</p>")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

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
        self.add_nav_item("Dashboard Overview", PlaceholderScreen("Dashboard Overview"))
        
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
