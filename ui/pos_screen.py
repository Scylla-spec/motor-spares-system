"""
Modernized Point of Sale (POS) Screen for Motor Spares System.
Features:
- Two-column clean layout (Part Search on left, Cart & Checkout on right)
- Stock pill badges on search results
- Modern Totals & Payment Summary Card
- Prominent checkout actions
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QSpinBox, QSplitter, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from models.user import User
from models.sale import SaleItem
from managers.inventory_manager import search_parts, get_all_parts
from managers.sales_manager import process_sale
from managers.customer_manager import get_all_customers
from ui.theme import (
    StockBadgeDelegate, COLOR_BORDER, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_PRIMARY_ORANGE, COLOR_SUCCESS
)

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
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title = QLabel("Point of Sale")
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {COLOR_TEXT_PRIMARY};")
        subtitle = QLabel("Search parts, build orders, and process customer checkout.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT_SECONDARY};")
        header_box.addWidget(title)
        header_box.addWidget(subtitle)
        main_layout.addLayout(header_box)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #E2E8F0; width: 2px; }")
        main_layout.addWidget(splitter)

        # --- LEFT PANEL: Search and Inventory ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)

        left_header = QLabel("Part Catalog")
        left_header.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        left_layout.addWidget(left_header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Scan or type part number, name, brand...")
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self.perform_search)
        left_layout.addWidget(self.search_input)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["PART #", "NAME", "PRICE", "STOCK", "ACTION"])
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setItemDelegateForColumn(3, StockBadgeDelegate(self.results_table))
        left_layout.addWidget(self.results_table)

        splitter.addWidget(left_widget)

        # --- RIGHT PANEL: Cart & Checkout ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)

        right_header = QLabel("Active Order Cart")
        right_header.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        right_layout.addWidget(right_header)

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHorizontalHeaderLabels(["PART #", "NAME", "QTY", "SUBTOTAL", "ACTION"])
        c_header = self.cart_table.horizontalHeader()
        c_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        c_header.setSectionResizeMode(1, QHeaderView.Stretch)
        c_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        c_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        c_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cart_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.cart_table)

        # Checkout & Customer card
        checkout_card = QFrame()
        checkout_card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        card_layout = QVBoxLayout(checkout_card)
        card_layout.setSpacing(10)

        # Total amount label
        self.total_label = QLabel("Total: $0.00")
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: 800;
            color: {COLOR_TEXT_PRIMARY};
        """)
        card_layout.addWidget(self.total_label)

        # Customer & Payment fields
        form_row = QHBoxLayout()
        form_row.setSpacing(10)

        cust_box = QVBoxLayout()
        cust_label = QLabel("Customer:")
        cust_label.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_SECONDARY};")
        self.customer_combo = QComboBox()
        cust_box.addWidget(cust_label)
        cust_box.addWidget(self.customer_combo)
        form_row.addLayout(cust_box)

        pay_box = QVBoxLayout()
        pay_label = QLabel("Payment Method:")
        pay_label.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_SECONDARY};")
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Cash", "EcoCash", "Card"])
        pay_box.addWidget(pay_label)
        pay_box.addWidget(self.payment_combo)
        form_row.addLayout(pay_box)

        card_layout.addLayout(form_row)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.cancel_sale_btn = QPushButton("Cancel Order")
        self.cancel_sale_btn.setFixedHeight(42)
        self.cancel_sale_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #EF4444;
                border: 1px solid #FECACA;
                font-weight: 600;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
            }
        """)
        self.cancel_sale_btn.clicked.connect(self.cancel_sale)
        btn_row.addWidget(self.cancel_sale_btn)

        self.checkout_btn = QPushButton("Complete Sale")
        self.checkout_btn.setFixedHeight(42)
        self.checkout_btn.setCursor(Qt.PointingHandCursor)
        self.checkout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: 700;
                font-size: 14px;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
        """)
        self.checkout_btn.clicked.connect(self.checkout)
        btn_row.addWidget(self.checkout_btn)

        card_layout.addLayout(btn_row)

        right_layout.addWidget(checkout_card)
        splitter.addWidget(right_widget)
        splitter.setSizes([550, 450])

    def refresh_customers(self):
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

        active_results = [p for p in results if not p.name.startswith("[DEACTIVATED]")]
        self.results_table.setRowCount(len(active_results))
        for row, part in enumerate(active_results):
            part_num_item = QTableWidgetItem(part.part_number)
            font = QFont()
            font.setBold(True)
            part_num_item.setFont(font)
            self.results_table.setItem(row, 0, part_num_item)

            self.results_table.setItem(row, 1, QTableWidgetItem(part.name))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"${part.selling_price:.2f}"))

            stock_item = QTableWidgetItem(str(part.quantity_on_hand))
            stock_item.setData(Qt.UserRole + 1, part.is_low_stock())
            self.results_table.setItem(row, 3, stock_item)

            add_btn = QPushButton("+ Add")
            add_btn.setFixedHeight(26)
            add_btn.setEnabled(part.quantity_on_hand > 0)
            if part.quantity_on_hand > 0:
                add_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLOR_PRIMARY_ORANGE};
                        color: white;
                        font-weight: bold;
                        border-radius: 4px;
                    }}
                """)
            add_btn.clicked.connect(lambda checked, p=part: self.add_to_cart(p))
            self.results_table.setCellWidget(row, 4, add_btn)

    def add_to_cart(self, part):
        if part.part_id in self.cart_items:
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
            part_num_item = QTableWidgetItem(item.part_number)
            font = QFont()
            font.setBold(True)
            part_num_item.setFont(font)
            self.cart_table.setItem(row, 0, part_num_item)

            self.cart_table.setItem(row, 1, QTableWidgetItem(item.part_name))

            qty_spin = QSpinBox()
            qty_spin.setMinimum(1)
            qty_spin.setMaximum(100000)
            qty_spin.setValue(item.quantity)
            qty_spin.setFixedHeight(28)
            qty_spin.valueChanged.connect(lambda val, pid=part_id: self.change_cart_qty(pid, val))
            self.cart_table.setCellWidget(row, 2, qty_spin)

            self.cart_table.setItem(row, 3, QTableWidgetItem(f"${item.subtotal:.2f}"))

            remove_btn = QPushButton("✕")
            remove_btn.setToolTip("Remove from cart")
            remove_btn.setFixedSize(28, 28)
            remove_btn.setStyleSheet("""
                QPushButton {
                    color: #EF4444;
                    border: 1px solid #FECACA;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #FEF2F2;
                }
            """)
            remove_btn.clicked.connect(lambda checked, pid=part_id: self.remove_from_cart(pid))
            self.cart_table.setCellWidget(row, 4, remove_btn)

            total_amount += item.subtotal

        self.total_label.setText(f"Total: ${total_amount:.2f}")

    def change_cart_qty(self, part_id, new_qty):
        if part_id in self.cart_items:
            self.cart_items[part_id].quantity = new_qty
            self.update_cart_display()

    def remove_from_cart(self, part_id):
        if part_id in self.cart_items:
            del self.cart_items[part_id]
            self.update_cart_display()

    def cancel_sale(self):
        if not self.cart_items:
            return
        confirm = QMessageBox.question(
            self, "Cancel Sale",
            "Discard the current cart? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.cart_items.clear()
            self.update_cart_display()

    def checkout(self):
        if not self.cart_items:
            QMessageBox.warning(self, "Empty Cart", "Cannot checkout an empty cart.")
            return

        payment_method = self.payment_combo.currentText()
        customer_id = self.customer_combo.currentData()
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
            self.perform_search("")
        else:
            QMessageBox.critical(self, "Checkout Failed", result_msg)