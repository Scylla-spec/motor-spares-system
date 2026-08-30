"""
Pay Later / On Credit Management Screen for Motor Spares System.
Allows tracking goods issued to known customers on credit, recording pending transactions,
viewing itemized details, and settling accounts when customers pay.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QComboBox, QDateEdit,
    QTextEdit, QFrame, QTabWidget, QSpinBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from models.user import User
from models.credit_order import CreditOrder
from managers.credit_manager import (
    create_credit_order, get_credit_orders, get_credit_order_items,
    mark_credit_order_paid, get_credit_summary
)
from managers.customer_manager import get_all_customers
from managers.inventory_manager import get_all_parts
from ui.theme import (
    MetricStatCard, create_orange_button, StockBadgeDelegate,
    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_PRIMARY_ORANGE, ScreenHeader, ICON_CREDIT, COLOR_SUCCESS
)


class CreditOrderItemsDialog(QDialog):
    """Dialog showing the itemized parts and quantities taken in a credit order."""
    def __init__(self, order: CreditOrder, parent=None):
        super().__init__(parent)
        self.order = order
        self.setWindowTitle(f"Credit Order #{order.credit_id} — {order.customer_name}")
        self.resize(620, 380)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"Items for Credit Order #{self.order.credit_id}")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        info_label = QLabel(
            f"Customer: <b>{self.order.customer_name}</b> | Phone: <b>{self.order.customer_phone or '—'}</b> | "
            f"Status: <b>{self.order.status}</b> | Total: <b>${self.order.total_amount:.2f}</b>"
        )
        info_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(info_label)

        if self.order.notes:
            notes_label = QLabel(f"Notes: {self.order.notes}")
            notes_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; font-style: italic;")
            layout.addWidget(notes_label)

        # Table of items
        items = get_credit_order_items(self.order.credit_id)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Part#", "Part Name", "Quantity", "Unit Price", "Subtotal"])
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        table.setRowCount(len(items))
        for row, it in enumerate(items):
            pnum_item = QTableWidgetItem(it.part_number)
            font = QFont()
            font.setBold(True)
            pnum_item.setFont(font)
            table.setItem(row, 0, pnum_item)

            table.setItem(row, 1, QTableWidgetItem(it.part_name))
            table.setItem(row, 2, QTableWidgetItem(str(it.quantity)))
            table.setItem(row, 3, QTableWidgetItem(f"${it.unit_price:.2f}"))
            table.setItem(row, 4, QTableWidgetItem(f"${it.subtotal:.2f}"))

        layout.addWidget(table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


class RecordCreditSaleDialog(QDialog):
    """Dialog to record a new credit sale with customer selection and searchable item picker."""
    def __init__(self, cashier_id: int, parent=None):
        super().__init__(parent)
        self.cashier_id = cashier_id
        self._customers = get_all_customers()
        self._all_in_stock_parts = [
            p for p in get_all_parts()
            if not p.name.startswith("[DEACTIVATED]") and p.quantity_on_hand > 0
        ]
        self._filtered_parts = list(self._all_in_stock_parts)
        self.selected_items = []  # list of dicts

        self.setWindowTitle("Record New Credit Sale (Pay Later)")
        self.resize(700, 560)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Issue Goods on Credit (Pay Later)")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        # Customer Section
        cust_form = QFormLayout()
        cust_form.setSpacing(8)

        self.cust_combo = QComboBox()
        self.cust_combo.addItem("-- Select Existing Customer or Type Below --", None)
        for c in self._customers:
            self.cust_combo.addItem(f"{c.name} ({c.phone or 'No phone'})", c.customer_id)
        self.cust_combo.currentIndexChanged.connect(self._on_customer_selected)
        cust_form.addRow("Existing Customer:", self.cust_combo)

        self.cust_name_input = QLineEdit()
        self.cust_name_input.setPlaceholderText("Customer Name * (e.g. John Moyo)")
        cust_form.addRow("Customer Name *:", self.cust_name_input)

        self.cust_phone_input = QLineEdit()
        self.cust_phone_input.setPlaceholderText("Customer Phone (optional)")
        cust_form.addRow("Phone:", self.cust_phone_input)

        self.due_date_input = QDateEdit(QDate.currentDate().addDays(7))
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDisplayFormat("yyyy-MM-dd")
        cust_form.addRow("Promised Pay Date:", self.due_date_input)

        layout.addLayout(cust_form)

        # Item Selection Section
        item_box = QFrame()
        item_box.setStyleSheet(f"""
            QFrame {{
                background-color: #F8FAFC;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        item_layout = QVBoxLayout(item_box)
        item_layout.setSpacing(8)

        item_header_layout = QHBoxLayout()
        item_header = QLabel("Search & Add Items Taken on Credit:")
        item_header.setStyleSheet(f"font-weight: 700; font-size: 12px; color: {COLOR_TEXT_PRIMARY};")
        item_header_layout.addWidget(item_header)

        self.search_status_lbl = QLabel(f"{len(self._all_in_stock_parts)} in-stock parts available")
        self.search_status_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_SECONDARY};")
        item_header_layout.addStretch()
        item_header_layout.addWidget(self.search_status_lbl)
        item_layout.addLayout(item_header_layout)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Type part number (e.g. AC3032), name, vehicle, or brand to search...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._on_search_return_pressed)
        item_layout.addWidget(self.search_input)

        # Dropdown selection + Quantity + Add button
        add_row = QHBoxLayout()
        add_row.setSpacing(8)

        self.part_combo = QComboBox()
        self.part_combo.setMinimumWidth(320)
        self.part_combo.currentIndexChanged.connect(self._on_part_selection_changed)
        add_row.addWidget(self.part_combo, 3)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 1000)
        self.qty_spin.setValue(1)
        self.qty_spin.setFixedWidth(70)
        self.qty_spin.setToolTip("Quantity to take on credit")
        add_row.addWidget(self.qty_spin)

        self.add_item_btn = QPushButton("+ Add to List")
        self.add_item_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
            QPushButton:disabled {{
                background-color: #CBD5E1;
                color: #64748B;
            }}
        """)
        self.add_item_btn.clicked.connect(self._add_item_to_table)
        add_row.addWidget(self.add_item_btn)
        item_layout.addLayout(add_row)

        layout.addWidget(item_box)

        # Populate initial parts list
        self._populate_parts_combo()

        # Selected items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(["Part#", "Part Name", "Qty", "Unit Price", "Subtotal", "Action"])
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.items_table)

        # Total label & Notes
        bottom_row = QHBoxLayout()
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Notes / terms (e.g. Will pay half tomorrow)")
        bottom_row.addWidget(self.notes_input, 2)

        self.total_label = QLabel("Total: $0.00")
        self.total_label.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {COLOR_TEXT_PRIMARY};")
        bottom_row.addWidget(self.total_label, 1)
        layout.addLayout(bottom_row)

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("Confirm Credit Sale")
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: 700;
                border-radius: 6px;
                padding: 6px 18px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
        """)
        confirm_btn.clicked.connect(self._save_credit_order)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def _populate_parts_combo(self):
        self.part_combo.blockSignals(True)
        self.part_combo.clear()
        if not self._filtered_parts:
            self.part_combo.addItem("-- No matching parts in stock --", None)
            self.part_combo.setEnabled(False)
            self.qty_spin.setEnabled(False)
            self.add_item_btn.setEnabled(False)
            self.search_status_lbl.setText("0 matches")
        else:
            self.part_combo.setEnabled(True)
            self.qty_spin.setEnabled(True)
            self.add_item_btn.setEnabled(True)
            for p in self._filtered_parts:
                self.part_combo.addItem(
                    f"{p.part_number} — {p.name} (Stock: {p.quantity_on_hand}, ${p.selling_price:.2f})",
                    p.part_id
                )
            count = len(self._filtered_parts)
            self.search_status_lbl.setText(f"{count} item{'s' if count != 1 else ''} available")

        self.part_combo.blockSignals(False)
        self._on_part_selection_changed(self.part_combo.currentIndex())

    def _on_search_text_changed(self, text: str):
        query = text.strip().lower()
        if not query:
            self._filtered_parts = list(self._all_in_stock_parts)
        else:
            self._filtered_parts = [
                p for p in self._all_in_stock_parts
                if query in (p.part_number or "").lower()
                or query in (p.name or "").lower()
                or query in (p.brand or "").lower()
                or query in (p.category or "").lower()
                or query in (p.compatible_vehicles or "").lower()
            ]
        self._populate_parts_combo()

    def _on_search_return_pressed(self):
        # When hitting Enter in search bar, add selected item to list
        if self.part_combo.isEnabled() and self.part_combo.currentData() is not None:
            self._add_item_to_table()

    def _on_part_selection_changed(self, index: int):
        part_id = self.part_combo.currentData()
        if not part_id:
            return
        part = next((p for p in self._all_in_stock_parts if p.part_id == part_id), None)
        if part:
            self.qty_spin.setMaximum(max(1, part.quantity_on_hand))

    def _on_customer_selected(self, index):
        cust_id = self.cust_combo.currentData()
        if cust_id:
            for c in self._customers:
                if c.customer_id == cust_id:
                    self.cust_name_input.setText(c.name)
                    self.cust_phone_input.setText(c.phone or "")
                    break

    def _add_item_to_table(self):
        part_id = self.part_combo.currentData()
        if not part_id:
            return
        qty = self.qty_spin.value()

        part = next((p for p in self._all_in_stock_parts if p.part_id == part_id), None)
        if not part:
            return

        if qty > part.quantity_on_hand:
            QMessageBox.warning(self, "Stock Limit", f"Only {part.quantity_on_hand} available in stock.")
            return

        # Check if already in selected
        existing = next((it for it in self.selected_items if it["part_id"] == part_id), None)
        if existing:
            if existing["quantity"] + qty > part.quantity_on_hand:
                QMessageBox.warning(self, "Stock Limit", f"Cannot exceed available stock of {part.quantity_on_hand}.")
                return
            existing["quantity"] += qty
        else:
            self.selected_items.append({
                "part_id": part.part_id,
                "part_number": part.part_number,
                "part_name": part.name,
                "quantity": qty,
                "unit_price": part.selling_price
            })

        self._refresh_items_table()
        self.qty_spin.setValue(1)
        self.search_input.selectAll()
        self.search_input.setFocus()

    def _refresh_items_table(self):
        self.items_table.setRowCount(len(self.selected_items))
        total = 0.0
        for row, it in enumerate(self.selected_items):
            subtotal = it["quantity"] * it["unit_price"]
            pnum_item = QTableWidgetItem(it["part_number"])
            font = QFont()
            font.setBold(True)
            pnum_item.setFont(font)
            self.items_table.setItem(row, 0, pnum_item)
            self.items_table.setItem(row, 1, QTableWidgetItem(it["part_name"]))
            self.items_table.setItem(row, 2, QTableWidgetItem(str(it["quantity"])))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"${it['unit_price']:.2f}"))
            self.items_table.setItem(row, 4, QTableWidgetItem(f"${subtotal:.2f}"))

            remove_btn = QPushButton("Remove")
            remove_btn.setFixedHeight(24)
            remove_btn.setCursor(Qt.PointingHandCursor)
            remove_btn.setStyleSheet("""
                QPushButton {
                    color: #EF4444;
                    background: #FEF2F2;
                    border: 1px solid #FECACA;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background: #FEE2E2;
                    border-color: #FCA5A5;
                }
            """)
            remove_btn.clicked.connect(lambda checked, idx=row: self._remove_item(idx))
            self.items_table.setCellWidget(row, 5, remove_btn)

            total += subtotal

        self.total_label.setText(f"Total: ${total:.2f}")

    def _remove_item(self, idx):
        if 0 <= idx < len(self.selected_items):
            self.selected_items.pop(idx)
            self._refresh_items_table()

    def _save_credit_order(self):
        name = self.cust_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter the customer name.")
            return
        if not self.selected_items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one item.")
            return

        cust_id = self.cust_combo.currentData()
        phone = self.cust_phone_input.text().strip()
        due_date = self.due_date_input.date().toString("yyyy-MM-dd")
        notes = self.notes_input.text().strip()

        ok, msg, credit_id = create_credit_order(
            customer_name=name,
            items=self.selected_items,
            cashier_id=self.cashier_id,
            customer_id=cust_id,
            customer_phone=phone,
            due_date=due_date,
            notes=notes
        )

        if ok:
            QMessageBox.information(self, "Success", f"Credit order #{credit_id} created successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", msg)


class CreditScreen(QWidget):
    """
    Pay Later / On Credit Screen.
    Displays pending customer credit debts, settled history, and quick settlement actions.
    """
    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Header
        header_layout = QHBoxLayout()
        header_box = ScreenHeader(
            ICON_CREDIT,
            "Pay Later / On Credit",
            "Track goods taken on customer credit, outstanding debts, and settlements.",
            font_size=20,
        )
        header_layout.addWidget(header_box)

        header_layout.addStretch()

        # KPI Metric Cards
        self.outstanding_card = MetricStatCard("OUTSTANDING DEBT", "$0.00")
        self.pending_count_card = MetricStatCard("PENDING ORDERS", "0")
        header_layout.addWidget(self.outstanding_card)
        header_layout.addWidget(self.pending_count_card)

        # Record Credit Sale Button
        self.new_credit_btn = QPushButton("+ Record Credit Sale")
        self.new_credit_btn.setFixedHeight(44)
        self.new_credit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: 700;
                font-size: 13px;
                border: none;
                border-radius: 6px;
                padding: 0px 18px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
        """)
        self.new_credit_btn.clicked.connect(self.open_new_credit_dialog)
        header_layout.addWidget(self.new_credit_btn)

        layout.addLayout(header_layout)

        # Filter bar
        filter_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by customer name or phone...")
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self.apply_filter)
        filter_bar.addWidget(self.search_input)

        filter_bar.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filter_bar.addWidget(refresh_btn)

        layout.addLayout(filter_bar)

        # Tab Widget: Pending vs Settled
        self.tabs = QTabWidget()

        # Tab 1: Pending Orders
        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(8)
        self.pending_table.setHorizontalHeaderLabels([
            "Order#", "Date Taken", "Customer Name", "Phone", "Due Date", "Total Due", "Notes", "Actions"
        ])
        p_head = self.pending_table.horizontalHeader()
        p_head.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        p_head.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        p_head.setSectionResizeMode(2, QHeaderView.Stretch)
        p_head.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        p_head.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        p_head.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        p_head.setSectionResizeMode(6, QHeaderView.Stretch)
        p_head.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.pending_table.verticalHeader().setVisible(False)
        self.pending_table.verticalHeader().setDefaultSectionSize(42)
        self.pending_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pending_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabs.addTab(self.pending_table, "Pending Debts (Unpaid)")

        # Tab 2: Settled Orders
        self.paid_table = QTableWidget()
        self.paid_table.setColumnCount(7)
        self.paid_table.setHorizontalHeaderLabels([
            "Order#", "Date Taken", "Customer Name", "Phone", "Paid Date", "Amount Settled", "Actions"
        ])
        s_head = self.paid_table.horizontalHeader()
        s_head.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        s_head.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        s_head.setSectionResizeMode(2, QHeaderView.Stretch)
        s_head.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        s_head.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        s_head.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        s_head.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.paid_table.verticalHeader().setVisible(False)
        self.paid_table.verticalHeader().setDefaultSectionSize(42)
        self.paid_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.paid_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabs.addTab(self.paid_table, "Settled History (Paid)")

        layout.addWidget(self.tabs)

    def refresh(self):
        summary = get_credit_summary()
        self.outstanding_card.set_value(f"${summary['total_outstanding']:.2f}")
        self.pending_count_card.set_value(str(summary['pending_count']))
        self.apply_filter()

    def apply_filter(self):
        query = self.search_input.text().strip().lower()

        # Load Pending Orders
        pending_orders = get_credit_orders(status_filter="Pending")
        if query:
            pending_orders = [o for o in pending_orders if query in o.customer_name.lower() or (o.customer_phone and query in o.customer_phone.lower())]

        self.pending_table.setRowCount(len(pending_orders))
        for row, o in enumerate(pending_orders):
            id_item = QTableWidgetItem(f"#{o.credit_id}")
            f = QFont()
            f.setBold(True)
            id_item.setFont(f)
            self.pending_table.setItem(row, 0, id_item)

            self.pending_table.setItem(row, 1, QTableWidgetItem(o.created_at[:10]))
            self.pending_table.setItem(row, 2, QTableWidgetItem(o.customer_name))
            self.pending_table.setItem(row, 3, QTableWidgetItem(o.customer_phone or "—"))
            self.pending_table.setItem(row, 4, QTableWidgetItem(o.due_date or "—"))

            amt_item = QTableWidgetItem(f"${o.total_amount:.2f}")
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.pending_table.setItem(row, 5, amt_item)

            self.pending_table.setItem(row, 6, QTableWidgetItem(o.notes or "—"))

            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignCenter)

            view_btn = QPushButton("View Items")
            view_btn.setFixedHeight(28)
            view_btn.setMinimumWidth(75)
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #0F172A;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                    border-color: #94A3B8;
                }
            """)
            view_btn.clicked.connect(lambda checked, ord=o: self.view_items(ord))
            action_layout.addWidget(view_btn)

            pay_btn = QPushButton("Mark Paid")
            pay_btn.setFixedHeight(28)
            pay_btn.setMinimumWidth(75)
            pay_btn.setCursor(Qt.PointingHandCursor)
            pay_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #15803D;
                    border: 1px solid #86EFAC;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background-color: #F0FDF4;
                    border-color: #4ADE80;
                }
            """)
            pay_btn.clicked.connect(lambda checked, ord=o: self.settle_order(ord))
            action_layout.addWidget(pay_btn)

            self.pending_table.setCellWidget(row, 7, action_widget)

        # Load Paid Orders
        paid_orders = get_credit_orders(status_filter="Paid")
        if query:
            paid_orders = [o for o in paid_orders if query in o.customer_name.lower() or (o.customer_phone and query in o.customer_phone.lower())]

        self.paid_table.setRowCount(len(paid_orders))
        for row, o in enumerate(paid_orders):
            id_item = QTableWidgetItem(f"#{o.credit_id}")
            f = QFont()
            f.setBold(True)
            id_item.setFont(f)
            self.paid_table.setItem(row, 0, id_item)

            self.paid_table.setItem(row, 1, QTableWidgetItem(o.created_at[:10]))
            self.paid_table.setItem(row, 2, QTableWidgetItem(o.customer_name))
            self.paid_table.setItem(row, 3, QTableWidgetItem(o.customer_phone or "—"))
            self.paid_table.setItem(row, 4, QTableWidgetItem((o.paid_at or "")[:19].replace("T", " ")))

            amt_item = QTableWidgetItem(f"${o.amount_paid:.2f}")
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.paid_table.setItem(row, 5, amt_item)

            paid_action_widget = QWidget()
            paid_action_layout = QHBoxLayout(paid_action_widget)
            paid_action_layout.setContentsMargins(4, 2, 4, 2)
            paid_action_layout.setAlignment(Qt.AlignCenter)

            view_btn = QPushButton("View Items")
            view_btn.setFixedHeight(28)
            view_btn.setMinimumWidth(80)
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #0F172A;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                    border-color: #94A3B8;
                }
            """)
            view_btn.clicked.connect(lambda checked, ord=o: self.view_items(ord))
            paid_action_layout.addWidget(view_btn)
            self.paid_table.setCellWidget(row, 6, paid_action_widget)

    def open_new_credit_dialog(self):
        dialog = RecordCreditSaleDialog(cashier_id=self.current_user.user_id, parent=self)
        if dialog.exec():
            self.refresh()

    def view_items(self, order: CreditOrder):
        dialog = CreditOrderItemsDialog(order=order, parent=self)
        dialog.exec()

    def settle_order(self, order: CreditOrder):
        # Choose payment method
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Settle Credit Order #{order.credit_id}")
        dialog.resize(350, 160)
        d_layout = QVBoxLayout(dialog)
        d_layout.setSpacing(12)

        prompt = QLabel(f"Settle <b>${order.total_amount:.2f}</b> from <b>{order.customer_name}</b>?")
        d_layout.addWidget(prompt)

        form = QFormLayout()
        pay_combo = QComboBox()
        pay_combo.addItems(["Cash", "EcoCash", "Card"])
        form.addRow("Payment Method:", pay_combo)
        d_layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(c_btn)

        confirm_btn = QPushButton("Confirm Payment")
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SUCCESS};
                color: white;
                font-weight: 700;
                border-radius: 4px;
                padding: 6px 14px;
            }}
        """)
        confirm_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(confirm_btn)
        d_layout.addLayout(btn_row)

        if dialog.exec():
            method = pay_combo.currentText()
            ok, msg = mark_credit_order_paid(
                credit_id=order.credit_id,
                payment_method=method,
                cashier_id=self.current_user.user_id,
                cashier_name=self.current_user.username
            )
            if ok:
                QMessageBox.information(self, "Payment Received", msg)
                self.refresh()
            else:
                QMessageBox.critical(self, "Error", msg)
