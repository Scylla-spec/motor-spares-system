from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QSpinBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from models.user import User
from models.sale import SaleItem
from managers.inventory_manager import search_parts, get_all_parts
from managers.sales_manager import process_sale
from managers.customer_manager import get_all_customers

class POSScreen(QWidget):
    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.cart_items = {}  # part_id -> SaleItem
        self._customers = []  # cached customer list
        self.setup_ui()
        self.perform_search("")  # Load initial parts
        self.refresh_customers()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # --- LEFT PANEL: Search and Inventory ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_layout.addWidget(QLabel("<h3>Part Search</h3>"))
        
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Scan or type part number / name...")
        self.search_input.textChanged.connect(self.perform_search)
        search_layout.addWidget(self.search_input)
        left_layout.addLayout(search_layout)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Part #", "Name", "Price", "Stock", "Action"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        left_layout.addWidget(self.results_table)
        
        splitter.addWidget(left_widget)
        
        # --- RIGHT PANEL: Cart & Checkout ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        right_layout.addWidget(QLabel("<h3>Current Cart</h3>"))
        
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHorizontalHeaderLabels(["Part #", "Name", "Qty", "Subtotal", "Action"])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cart_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.cart_table)
        
        # Totals and Checkout area
        checkout_layout = QVBoxLayout()
        
        self.total_label = QLabel("<h2>Total: $0.00</h2>")
        self.total_label.setAlignment(Qt.AlignRight)
        checkout_layout.addWidget(self.total_label)
        
        # Customer selection
        customer_layout = QHBoxLayout()
        customer_layout.addWidget(QLabel("Customer:"))
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(180)
        customer_layout.addWidget(self.customer_combo)
        checkout_layout.addLayout(customer_layout)
        
        payment_layout = QHBoxLayout()
        payment_layout.addWidget(QLabel("Payment Method:"))
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Cash", "EcoCash", "Card"])
        payment_layout.addWidget(self.payment_combo)
        checkout_layout.addLayout(payment_layout)
        
        self.checkout_btn = QPushButton("Complete Sale")
        self.checkout_btn.setMinimumHeight(50)
        self.checkout_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; font-size: 16px;")
        self.checkout_btn.clicked.connect(self.checkout)
        checkout_layout.addWidget(self.checkout_btn)
        
        right_layout.addLayout(checkout_layout)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])

    def refresh_customers(self):
        """Re-loads the customer list into the customer combobox."""
        self._customers = get_all_customers()
        self.customer_combo.clear()
        self.customer_combo.addItem("Walk-in", None)
        for c in self._customers:
            self.customer_combo.addItem(c.name, c.customer_id)

    def perform_search(self, text):
        if not text.strip():
            results = get_all_parts()
        else:
            results = search_parts(text)
            
        # Filter out deactivated
        active_results = [p for p in results if not p.name.startswith("[DEACTIVATED]")]
            
        self.results_table.setRowCount(len(active_results))
        for row, part in enumerate(active_results):
            self.results_table.setItem(row, 0, QTableWidgetItem(part.part_number))
            self.results_table.setItem(row, 1, QTableWidgetItem(part.name))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"${part.selling_price:.2f}"))
            
            stock_item = QTableWidgetItem(str(part.quantity_on_hand))
            if part.quantity_on_hand <= 0:
                stock_item.setBackground(QColor("#ffcccc"))
                stock_item.setForeground(QColor("black"))
            self.results_table.setItem(row, 3, stock_item)
            
            add_btn = QPushButton("Add to Cart")
            add_btn.setEnabled(part.quantity_on_hand > 0)
            add_btn.clicked.connect(lambda checked, p=part: self.add_to_cart(p))
            self.results_table.setCellWidget(row, 4, add_btn)

    def add_to_cart(self, part):
        if part.part_id in self.cart_items:
            # Check stock limit
            if self.cart_items[part.part_id].quantity >= part.quantity_on_hand:
                QMessageBox.warning(self, "Stock Limit", f"Cannot add more {part.name}. Only {part.quantity_on_hand} in stock.")
                return
            self.cart_items[part.part_id].quantity += 1
        else:
            self.cart_items[part.part_id] = SaleItem(
                sale_item_id=None,
                sale_id=None,
                part_id=part.part_id,
                quantity=1,
                unit_price=part.selling_price,
                part_name=part.name,
                part_number=part.part_number
            )
            
        self.update_cart_display()

    def update_cart_display(self):
        self.cart_table.setRowCount(len(self.cart_items))
        total_amount = 0.0
        
        for row, (part_id, item) in enumerate(self.cart_items.items()):
            self.cart_table.setItem(row, 0, QTableWidgetItem(item.part_number))
            self.cart_table.setItem(row, 1, QTableWidgetItem(item.part_name))
            
            # Spinbox for quantity
            qty_spin = QSpinBox()
            qty_spin.setMinimum(1)
            qty_spin.setMaximum(100000)
            qty_spin.setValue(item.quantity)
            qty_spin.valueChanged.connect(lambda val, pid=part_id: self.change_cart_qty(pid, val))
            self.cart_table.setCellWidget(row, 2, qty_spin)
            
            self.cart_table.setItem(row, 3, QTableWidgetItem(f"${item.subtotal:.2f}"))
            
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda checked, pid=part_id: self.remove_from_cart(pid))
            self.cart_table.setCellWidget(row, 4, remove_btn)
            
            total_amount += item.subtotal
            
        self.total_label.setText(f"<h2>Total: ${total_amount:.2f}</h2>")

    def change_cart_qty(self, part_id, new_qty):
        if part_id in self.cart_items:
            # We would ideally re-check max stock here from DB, but for simple UI logic 
            # we allow it and rely on checkout validation to catch race conditions.
            self.cart_items[part_id].quantity = new_qty
            self.update_cart_display()

    def remove_from_cart(self, part_id):
        if part_id in self.cart_items:
            del self.cart_items[part_id]
            self.update_cart_display()

    def checkout(self):
        if not self.cart_items:
            QMessageBox.warning(self, "Empty Cart", "Cannot checkout an empty cart.")
            return
            
        payment_method = self.payment_combo.currentText()
        customer_id = self.customer_combo.currentData()   # None = Walk-in
        customer_name = self.customer_combo.currentText()
        items = list(self.cart_items.values())
        
        success, result_msg = process_sale(
            cart_items=items,
            payment_method=payment_method,
            cashier_id=self.current_user.user_id,
            cashier_name=self.current_user.username,
            customer_id=customer_id,
            customer_name=customer_name
        )
        
        if success:
            QMessageBox.information(self, "Sale Complete", f"Sale completed successfully!\nReceipt generated at:\n{result_msg}")
            self.cart_items.clear()
            self.update_cart_display()
            self.search_input.clear()
            self.perform_search("")  # Refresh inventory counts
        else:
            QMessageBox.critical(self, "Checkout Failed", result_msg)
