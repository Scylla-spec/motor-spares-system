"""
Point of Sale (POS) Screen for Motor Spares System.
Features:
- Streamlined two-column layout (Part Catalog on left, Active Order Cart on right)
- Distinct, unmistakable +/- quantity controls in cart
- Immediate stock availability badges
- Support for immediate checkout (Cash, EcoCash, Card) and Pay Later (On Credit)
- Clean, high-contrast, emoji-free modern UI
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QSplitter, QFrame, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from models.user import User
from models.sale import SaleItem
from managers.inventory_manager import search_parts, get_all_parts
from managers.sales_manager import process_sale
from managers.customer_manager import get_all_customers
from managers.credit_manager import create_credit_order
from managers.settings_manager import get_all_settings
from utils.thermal_receipt import print_credit_thermal_receipt
from utils.currency_engine import get_all_currency_equivalents, calculate_tender_change, format_currency
from utils.whatsapp_helper import build_pos_receipt_message, open_whatsapp_chat
from ui.theme import (
    MetricStatCard, StockBadgeDelegate, create_primary_action_button,
    create_orange_button, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_PRIMARY_ORANGE, PlusMinusSpinBox, ScreenHeader, ICON_POS, QuantityStepper,
    set_btn_icon, ICON_TRASH, ICON_REFRESH, ICON_WHATSAPP
)


class POSScreen(QWidget):
    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.cart_items = {}  # part_id -> SaleItem
        self._customers = []  # cached customer list
        self.setup_ui()
        self.perform_search("")  # Load initial catalog
        self.refresh_customers()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # Header
        main_layout.addWidget(ScreenHeader(
            ICON_POS,
            "Point of Sale",
            "Search parts, build active orders, and process customer checkout.",
            font_size=20,
        ))

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #E2E8F0; width: 2px; }")
        main_layout.addWidget(splitter, 1)

        # --- LEFT PANEL: Search and Inventory ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        # Header row with label + refresh button
        catalog_header_row = QHBoxLayout()
        left_header = QLabel("Part Catalog")
        left_header.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        catalog_header_row.addWidget(left_header)
        catalog_header_row.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setFixedHeight(28)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setToolTip("Reload parts from inventory (picks up newly stocked items)")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #F1F5F9;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
                font-size: 12px;
                font-weight: 600;
                padding: 0px 10px;
            }}
            QPushButton:hover {{
                background-color: #E2E8F0;
                border-color: #94A3B8;
            }}
            QPushButton:pressed {{
                background-color: #CBD5E1;
            }}
        """)
        self.refresh_btn.clicked.connect(self.refresh_catalog)
        set_btn_icon(self.refresh_btn, ICON_REFRESH, size=14, color='#475569')
        catalog_header_row.addWidget(self.refresh_btn)
        left_layout.addLayout(catalog_header_row)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Scan barcode or search by part#, name, brand...")
        self.search_input.setFixedHeight(34)
        self.search_input.textChanged.connect(self.perform_search)
        left_layout.addWidget(self.search_input)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(["#", "Part#", "Name", "Price", "Stock", "Action"])
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.results_table.setColumnWidth(5, 100)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.verticalHeader().setDefaultSectionSize(44)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setItemDelegateForColumn(4, StockBadgeDelegate(self.results_table))
        left_layout.addWidget(self.results_table)

        splitter.addWidget(left_widget)

        # --- RIGHT PANEL: Cart & Checkout ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        right_header = QLabel("Active Order Cart")
        right_header.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        right_layout.addWidget(right_header)

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHorizontalHeaderLabels(["Part#", "Name", "Quantity", "Subtotal", "Action"])
        c_header = self.cart_table.horizontalHeader()
        c_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        c_header.setSectionResizeMode(1, QHeaderView.Stretch)
        c_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cart_table.setColumnWidth(2, 130)
        c_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.cart_table.setColumnWidth(3, 90)
        c_header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(4, 75)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.verticalHeader().setDefaultSectionSize(38)
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
                padding: 10px;
            }}
        """)
        card_layout = QVBoxLayout(checkout_card)
        card_layout.setSpacing(8)

        # Total amount label
        self.total_label = QLabel("Total: $0.00")
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 800;
            color: {COLOR_TEXT_PRIMARY};
        """)
        card_layout.addWidget(self.total_label)

        # Multi-currency live equivalent chips
        self.currency_chips_label = QLabel("~ 0.00 ZiG  |  ~ R 0.00")
        self.currency_chips_label.setAlignment(Qt.AlignRight)
        self.currency_chips_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 700;
            color: #0284C7;
            padding: 1px 2px;
        """)
        card_layout.addWidget(self.currency_chips_label)

        # Customer & Payment fields
        form_row = QHBoxLayout()
        form_row.setSpacing(8)

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
        self.payment_combo.addItems(["Cash", "EcoCash", "Card", "Pay Later (On Credit)"])
        pay_box.addWidget(pay_label)
        pay_box.addWidget(self.payment_combo)
        form_row.addLayout(pay_box)

        card_layout.addLayout(form_row)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.cancel_sale_btn = QPushButton("Clear Cart")
        self.cancel_sale_btn.setFixedHeight(38)
        self.cancel_sale_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #EF4444;
                border: 1px solid #FECACA;
                font-weight: 700;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
            }
        """)
        self.cancel_sale_btn.clicked.connect(self.cancel_sale)
        btn_row.addWidget(self.cancel_sale_btn)

        self.checkout_btn = QPushButton("Complete Sale")
        self.checkout_btn.setFixedHeight(38)
        self.checkout_btn.setCursor(Qt.PointingHandCursor)
        self.checkout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: 700;
                font-size: 13px;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
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
        splitter.setSizes([560, 440])

    def refresh_customers(self):
        self._customers = get_all_customers()
        self.customer_combo.clear()
        self.customer_combo.addItem("Walk-in", None)
        for c in self._customers:
            self.customer_combo.addItem(c.name, c.customer_id)

    def perform_search(self, text):
        text_clean = text.strip()
        if not text_clean:
            results = get_all_parts()
        else:
            results = search_parts(text_clean)

        active_results = [p for p in results if not p.name.startswith("[DEACTIVATED]")]
        display_results = active_results[:150]

        self.results_table.setUpdatesEnabled(False)
        try:
            self.results_table.setRowCount(len(display_results))
            for row, part in enumerate(display_results):
                # 0: ROW # INDEX
                row_idx_item = QTableWidgetItem(str(row + 1))
                row_idx_item.setForeground(QColor("#64748B"))
                row_idx_item.setTextAlignment(Qt.AlignCenter)
                self.results_table.setItem(row, 0, row_idx_item)

                # 1: PART #
                part_num_item = QTableWidgetItem(part.part_number)
                font = QFont()
                font.setBold(True)
                part_num_item.setFont(font)
                self.results_table.setItem(row, 1, part_num_item)

                # 2: NAME
                self.results_table.setItem(row, 2, QTableWidgetItem(part.name))

                # 3: PRICE
                self.results_table.setItem(row, 3, QTableWidgetItem(f"${part.selling_price:.2f}"))

                # 4: STOCK (StockBadgeDelegate on Column 4)
                stock_item = QTableWidgetItem(str(part.quantity_on_hand))
                stock_item.setData(Qt.UserRole + 1, part.is_low_stock())
                self.results_table.setItem(row, 4, stock_item)

                # 5: ACTION
                add_widget = QWidget()
                add_layout = QHBoxLayout(add_widget)
                add_layout.setContentsMargins(4, 2, 4, 2)
                add_layout.setAlignment(Qt.AlignCenter)

                if part.quantity_on_hand > 0:
                    add_btn = QPushButton("+ Add")
                    add_btn.setFixedSize(72, 34)
                    add_btn.setCursor(Qt.PointingHandCursor)
                    add_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {COLOR_PRIMARY_ORANGE};
                            color: #FFFFFF;
                            font-weight: 700;
                            font-size: 13px;
                            border: none;
                            border-radius: 5px;
                            padding: 0px;
                        }}
                        QPushButton:hover {{
                            background-color: #EA580C;
                        }}
                        QPushButton:pressed {{
                            background-color: #C2410C;
                        }}
                    """)
                    add_btn.clicked.connect(lambda checked, p=part: self.add_to_cart(p))
                    add_layout.addWidget(add_btn)
                else:
                    disabled_btn = QPushButton("Out of Stock")
                    disabled_btn.setFixedSize(84, 34)
                    disabled_btn.setEnabled(False)
                    disabled_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #F1F5F9;
                            color: #94A3B8;
                            font-weight: 600;
                            font-size: 11px;
                            border: 1px solid #E2E8F0;
                            border-radius: 5px;
                            padding: 0px;
                        }
                    """)
                    add_layout.addWidget(disabled_btn)

                self.results_table.setCellWidget(row, 5, add_widget)
        finally:
            self.results_table.setUpdatesEnabled(True)

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
        items_list = list(self.cart_items.items())  # snapshot to avoid dict-change issues

        self.cart_table.setUpdatesEnabled(False)
        try:
            # Clear existing cell widgets before resizing to avoid Qt widget ownership issues
            for r in range(self.cart_table.rowCount()):
                self.cart_table.removeCellWidget(r, 2)
                self.cart_table.removeCellWidget(r, 4)

            self.cart_table.setRowCount(len(items_list))
            total_amount = 0.0

            for row, (part_id, item) in enumerate(items_list):
                # Col 0: Part Number
                part_num_item = QTableWidgetItem(item.part_number)
                font = QFont()
                font.setBold(True)
                part_num_item.setFont(font)
                self.cart_table.setItem(row, 0, part_num_item)

                # Col 1: Name
                self.cart_table.setItem(row, 1, QTableWidgetItem(item.part_name))

                # Col 2: Quantity stepper widget
                stepper = QuantityStepper(value=item.quantity, min_val=1, max_val=100000)
                stepper.set_on_change(lambda val, pid=part_id: self.change_cart_qty(pid, val))
                self.cart_table.setCellWidget(row, 2, stepper)

                # Col 3: Subtotal
                self.cart_table.setItem(row, 3, QTableWidgetItem(f"${item.subtotal:.2f}"))

                # Col 4: Delete button (wrapped in a widget for centering)
                del_widget = QWidget()
                del_layout = QHBoxLayout(del_widget)
                del_layout.setContentsMargins(2, 2, 2, 2)
                del_layout.setAlignment(Qt.AlignCenter)

                remove_btn = QPushButton()
                remove_btn.setToolTip("Remove from cart")
                remove_btn.setFixedSize(30, 28)
                remove_btn.setCursor(Qt.PointingHandCursor)
                remove_btn.setStyleSheet("""
                    QPushButton {
                        color: #DC2626;
                        background-color: #FFFFFF;
                        border: 1px solid #FECACA;
                        border-radius: 4px;
                        font-size: 14px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #FEF2F2;
                        border-color: #F87171;
                    }
                """)
                remove_btn.clicked.connect(lambda checked, pid=part_id: self.remove_from_cart(pid))
                set_btn_icon(remove_btn, ICON_TRASH, size=14, color='#DC2626')
                del_layout.addWidget(remove_btn)
                self.cart_table.setCellWidget(row, 4, del_widget)

                total_amount += item.subtotal
        finally:
            self.cart_table.setUpdatesEnabled(True)

        self._update_total_labels()

    def _update_total_labels(self):
        total_amount = sum(i.subtotal for i in self.cart_items.values())
        equiv = get_all_currency_equivalents(total_amount)
        self.total_label.setText(f"Total: ${total_amount:.2f}")
        self.currency_chips_label.setText(f"~ {equiv['ZIG']}   |   ~ {equiv['ZAR']}")

    def refresh_catalog(self):
        """Reload the full part catalog from the database (picks up newly stocked items)."""
        self.refresh_btn.setText("Refreshing...")
        self.refresh_btn.setEnabled(False)
        self.perform_search(self.search_input.text())
        self.refresh_btn.setText("Refresh")
        self.refresh_btn.setEnabled(True)

    def change_cart_qty(self, part_id, new_qty):
        if part_id in self.cart_items:
            self.cart_items[part_id].quantity = new_qty
            # Only update the subtotal cell — avoid full re-render which resets the stepper
            item = self.cart_items[part_id]
            # Find the row for this part_id
            items_list = list(self.cart_items.keys())
            if part_id in items_list:
                row = items_list.index(part_id)
                self.cart_table.setItem(row, 3, QTableWidgetItem(f"${item.subtotal:.2f}"))
            # Recalculate total
            self._update_total_labels()

    def remove_from_cart(self, part_id):
        if part_id in self.cart_items:
            del self.cart_items[part_id]
            self.update_cart_display()

    def cancel_sale(self):
        if not self.cart_items:
            return
        confirm = QMessageBox.question(
            self, "Clear Cart",
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

        if payment_method == "Pay Later (On Credit)":
            # Handle credit order
            if customer_name == "Walk-in":
                # Prompt for customer name
                cust_input, ok = QInputDialog.getText(
                    self, "Customer Name Required",
                    "Please enter the customer's name for this credit transaction:"
                )
                if not ok or not cust_input.strip():
                    QMessageBox.warning(self, "Required", "Customer name is required for credit transactions.")
                    return
                customer_name = cust_input.strip()

            credit_items = [
                {
                    "part_id": it.part_id,
                    "part_number": it.part_number,
                    "part_name": it.part_name,
                    "quantity": it.quantity,
                    "unit_price": it.unit_price
                }
                for it in items
            ]
            success, msg, credit_id = create_credit_order(
                customer_name=customer_name,
                items=credit_items,
                cashier_id=self.current_user.user_id,
                customer_id=customer_id
            )
            if success:
                # Attempt thermal credit docket print
                credit_prt_info = ""
                try:
                    p_ok, p_msg = print_credit_thermal_receipt(
                        credit_order_id=credit_id,
                        customer_name=customer_name,
                        items=credit_items,
                        total_amount=sum(it["quantity"] * it["unit_price"] for it in credit_items),
                        cashier_name=self.current_user.username
                    )
                    if p_ok:
                        credit_prt_info = "\n\nThermal receipt printed to receipt machine."
                except Exception as th_err:
                    import logging
                    logging.warning(f"Credit receipt thermal print error: {th_err}")

                QMessageBox.information(
                    self, "Credit Order Created",
                    f"Credit Order #{credit_id} recorded for {customer_name}!\n"
                    f"This transaction is now logged under the 'Pay Later / On Credit' tab as Pending.{credit_prt_info}"
                )
                self.cart_items.clear()
                self.update_cart_display()
                self.search_input.clear()
                self.perform_search("")
            else:
                QMessageBox.critical(self, "Credit Order Failed", msg)
            return

        total_checkout_amount = sum(it.subtotal for it in items)

        success, result_msg = process_sale(
            cart_items=items,
            payment_method=payment_method,
            cashier_id=self.current_user.user_id,
            cashier_name=self.current_user.username,
            customer_id=customer_id,
            customer_name=customer_name
        )

        if success:
            import os
            receipt_filename = os.path.basename(result_msg) if result_msg else "Receipt"
            rec_num = os.path.splitext(receipt_filename)[0]

            settings = get_all_settings()
            prt_name = settings.get("thermal_printer_name", "").strip()
            prt_info = f"Thermal receipt sent to: {prt_name}" if prt_name else "Note: You can configure a thermal receipt printer under Settings."

            equiv = get_all_currency_equivalents(total_checkout_amount)

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Sale Complete")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText(
                f"<b>Sale Completed Successfully!</b><br><br>"
                f"Receipt #: <b>{rec_num}</b><br>"
                f"Total Amount: <b>${total_checkout_amount:.2f}</b><br>"
                f"Equivalent: <b>{equiv['ZIG']}</b> &nbsp;|&nbsp; <b>{equiv['ZAR']}</b><br>"
                f"Payment Method: <b>{payment_method}</b><br><br>"
                f"{prt_info}"
            )
            wa_receipt_btn = msg_box.addButton("Send WhatsApp Receipt", QMessageBox.ActionRole)
            ok_btn = msg_box.addButton("Done", QMessageBox.AcceptRole)
            msg_box.setDefaultButton(ok_btn)

            msg_box.exec()

            if msg_box.clickedButton() == wa_receipt_btn:
                # Find phone for selected customer
                cust_phone = ""
                if customer_id:
                    for c in self._customers:
                        if c.customer_id == customer_id:
                            cust_phone = c.phone or ""
                            break

                if not cust_phone:
                    phone_input, p_ok = QInputDialog.getText(
                        self, "WhatsApp Receipt",
                        f"Enter customer WhatsApp phone number for {customer_name}:"
                    )
                    if p_ok and phone_input.strip():
                        cust_phone = phone_input.strip()

                if cust_phone:
                    wa_msg = build_pos_receipt_message(
                        customer_name=customer_name,
                        receipt_number=rec_num,
                        items=items,
                        total_amount=total_checkout_amount,
                        payment_method=payment_method
                    )
                    open_whatsapp_chat(cust_phone, wa_msg)

            self.cart_items.clear()
            self.update_cart_display()
            self.search_input.clear()
            self.perform_search("")
        else:
            QMessageBox.critical(self, "Checkout Failed", result_msg)