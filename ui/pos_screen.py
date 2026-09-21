"""
Point of Sale (POS) Screen for Motor Spares System.
Features:
- Streamlined two-column layout (Part Catalog on left, Active Order Cart on right)
- Editable unit-price per cart row for negotiated/discounted pricing
- Currency selector at checkout (USD / ZAR / ZiG) with live conversion
- Distinct, unmistakable +/- quantity controls in cart
- Immediate stock availability badges
- Support for immediate checkout (Cash, EcoCash, Card) and Pay Later (On Credit)
- Clean, high-contrast, emoji-free modern UI
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QSplitter, QFrame, QInputDialog,
    QApplication, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from models.user import User
from models.sale import SaleItem
from managers.inventory_manager import search_parts, get_all_parts
from managers.sales_manager import process_sale
from managers.customer_manager import get_all_customers
from managers.credit_manager import create_credit_order
from managers.settings_manager import get_all_settings
from utils.thermal_receipt import print_credit_thermal_receipt
from utils.currency_engine import get_all_currency_equivalents, calculate_tender_change, format_currency, get_exchange_rates
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

        # Debounce timer: fires 200ms after the user stops typing so we
        # don't open a new DB connection on every single keystroke.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_timer.timeout.connect(self._fire_search)

        self.setup_ui()
        self.perform_search("")  # Load initial catalog (bypasses timer)
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
        self.search_input.textChanged.connect(self._on_search_text_changed)
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
        self.results_table.setColumnWidth(5, 120)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.verticalHeader().setDefaultSectionSize(48)
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

        # Cart table: now 6 columns — Part#, Name, Unit Price (editable), Qty, Subtotal, Remove
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels(["Part#", "Name", "Unit Price", "Quantity", "Subtotal", ""])
        c_header = self.cart_table.horizontalHeader()
        c_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        c_header.setSectionResizeMode(1, QHeaderView.Stretch)
        c_header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(2, 95)
        c_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.cart_table.setColumnWidth(3, 130)
        c_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.cart_table.setColumnWidth(4, 85)
        c_header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(5, 40)
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

        # Total amount label (shows in selected currency)
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
            font-weight: 600;
            color: #475569;
            padding: 1px 2px;
        """)
        card_layout.addWidget(self.currency_chips_label)

        # Customer & Payment fields + Currency selector
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

        # Currency selector
        curr_box = QVBoxLayout()
        curr_label = QLabel("Currency:")
        curr_label.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_SECONDARY};")
        self.currency_combo = QComboBox()
        self.currency_combo.addItem("USD ($)", "USD")
        self.currency_combo.addItem("ZAR (R)", "ZAR")
        self.currency_combo.addItem("ZiG", "ZIG")
        self.currency_combo.setStyleSheet(f"""
            QComboBox {{
                font-weight: 700;
                color: {COLOR_TEXT_PRIMARY};
                background: #F8FAFC;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 4px 8px;
                min-height: 28px;
            }}
            QComboBox:focus {{
                border: 1px solid {COLOR_PRIMARY_ORANGE};
            }}
        """)
        self.currency_combo.currentIndexChanged.connect(self._on_currency_selection_changed)
        curr_box.addWidget(curr_label)
        curr_box.addWidget(self.currency_combo)
        form_row.addLayout(curr_box)

        card_layout.addLayout(form_row)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.cancel_sale_btn = QPushButton("Clear Cart")
        self.cancel_sale_btn.setFixedHeight(38)
        self.cancel_sale_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                font-weight: 600;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                border-color: #94A3B8;
                color: #0F172A;
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

    # ------------------------------------------------------------------
    # Search debounce helpers
    # ------------------------------------------------------------------
    def _on_search_text_changed(self, text: str):
        """Restart the debounce timer every time the text changes.
        The actual DB query only runs once the user pauses for 200ms."""
        self._search_timer.start()  # restarts if already running

    def _fire_search(self):
        """Called by the timer after the debounce delay expires."""
        self.perform_search(self.search_input.text())

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
            self.results_table.clearContents()
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
                # 7px top+bottom margin inside a 48px row leaves 34px for the
                # button. 106px wide in a 120px column (7px each side). That
                # gives a 106×34 shape — solid and balanced, not a pill.
                add_layout.setContentsMargins(7, 7, 7, 7)
                add_layout.setAlignment(Qt.AlignCenter)

                _BTN_W, _BTN_H = 106, 34  # identical for both states

                if part.quantity_on_hand > 0:
                    add_btn = QPushButton("+ Add")
                    add_btn.setFixedSize(_BTN_W, _BTN_H)
                    add_btn.setCursor(Qt.PointingHandCursor)
                    add_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {COLOR_PRIMARY_ORANGE};
                            color: #FFFFFF;
                            font-weight: 700;
                            font-size: 13px;
                            border: none;
                            border-radius: 6px;
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
                    disabled_btn.setFixedSize(_BTN_W, _BTN_H)
                    disabled_btn.setEnabled(False)
                    disabled_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #F1F5F9;
                            color: #64748B;
                            font-weight: 600;
                            font-size: 11px;
                            border: 1px solid #CBD5E1;
                            border-radius: 6px;
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
                part_number=part.part_number,
                original_unit_price=part.selling_price,  # Store catalogue price as original
            )
        self.update_cart_display()

    def update_cart_display(self):
        items_list = list(self.cart_items.items())  # snapshot to avoid dict-change issues

        self.cart_table.setUpdatesEnabled(False)
        try:
            # Clear existing cell widgets before resizing to avoid Qt widget ownership issues
            for r in range(self.cart_table.rowCount()):
                self.cart_table.removeCellWidget(r, 2)
                self.cart_table.removeCellWidget(r, 3)
                self.cart_table.removeCellWidget(r, 5)

            self.cart_table.setRowCount(len(items_list))

            for row, (part_id, item) in enumerate(items_list):
                # Col 0: Part Number
                part_num_item = QTableWidgetItem(item.part_number)
                font = QFont()
                font.setBold(True)
                part_num_item.setFont(font)
                self.cart_table.setItem(row, 0, part_num_item)

                # Col 1: Name
                self.cart_table.setItem(row, 1, QTableWidgetItem(item.part_name))

                # Col 2: Unit Price (editable spinbox — negotiable price)
                price_spin = QDoubleSpinBox()
                price_spin.setRange(0.00, 999999.99)
                price_spin.setDecimals(2)
                price_spin.setSingleStep(0.50)
                price_spin.setPrefix("$")
                price_spin.setValue(item.unit_price)
                price_spin.setFixedHeight(28)
                # Highlight in orange if the price was changed from the original
                is_negotiated = (item.original_unit_price is not None and
                                 abs(item.original_unit_price - item.unit_price) > 0.001)
                price_spin.setStyleSheet(f"""
                    QDoubleSpinBox {{
                        font-size: 12px;
                        font-weight: {'700' if is_negotiated else '500'};
                        color: {'#EA580C' if is_negotiated else '#0F172A'};
                        border: 1px solid {'#F97316' if is_negotiated else '#CBD5E1'};
                        border-radius: 4px;
                        padding: 2px 4px;
                        background: {'#FFF7ED' if is_negotiated else '#FFFFFF'};
                    }}
                    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                        width: 0; height: 0; border: none;
                    }}
                """)
                price_spin.valueChanged.connect(lambda val, pid=part_id: self.change_cart_price(pid, val))
                self.cart_table.setCellWidget(row, 2, price_spin)

                # Col 3: Quantity stepper widget
                stepper = QuantityStepper(value=item.quantity, min_val=1, max_val=100000)
                stepper.set_on_change(lambda val, pid=part_id: self.change_cart_qty(pid, val))
                self.cart_table.setCellWidget(row, 3, stepper)

                # Col 4: Subtotal
                self.cart_table.setItem(row, 4, QTableWidgetItem(f"${item.subtotal:.2f}"))

                # Col 5: Delete button
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
                        color: #475569;
                        background-color: #FFFFFF;
                        border: 1px solid #CBD5E1;
                        border-radius: 4px;
                        font-size: 14px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #F1F5F9;
                        border-color: #94A3B8;
                        color: #0F172A;
                    }
                """)
                remove_btn.clicked.connect(lambda checked, pid=part_id: self.remove_from_cart(pid))
                set_btn_icon(remove_btn, ICON_TRASH, size=14, color='#475569')
                del_layout.addWidget(remove_btn)
                self.cart_table.setCellWidget(row, 5, del_widget)

        finally:
            self.cart_table.setUpdatesEnabled(True)

        self._update_total_labels()

    def _get_selected_currency(self) -> str:
        """Returns the currency code currently selected in the checkout combo."""
        return self.currency_combo.currentData() or "USD"

    def _update_total_labels(self):
        total_usd = sum(i.subtotal for i in self.cart_items.values())
        equiv = get_all_currency_equivalents(total_usd)
        sel_curr = self._get_selected_currency()

        if sel_curr == "USD":
            self.total_label.setText(f"Total: ${total_usd:.2f}")
        elif sel_curr == "ZAR":
            rates = get_exchange_rates()
            zar_total = total_usd * rates.get("ZAR", 18.20)
            self.total_label.setText(f"Total: R {zar_total:,.2f}  (${total_usd:.2f} USD)")
        elif sel_curr == "ZIG":
            rates = get_exchange_rates()
            zig_total = total_usd * rates.get("ZIG", 26.50)
            self.total_label.setText(f"Total: {zig_total:,.2f} ZiG  (${total_usd:.2f} USD)")
        else:
            self.total_label.setText(f"Total: ${total_usd:.2f}")

        self.currency_chips_label.setText(f"~ {equiv['ZIG']}   |   ~ {equiv['ZAR']}")

    def _on_currency_selection_changed(self):
        """Called when the cashier switches the checkout currency dropdown."""
        self._update_total_labels()

    def refresh_catalog(self):
        """Reload the full part catalog from the database (picks up newly stocked items)."""
        self.refresh_btn.setText("Refreshing...")
        self.refresh_btn.setEnabled(False)
        QApplication.processEvents()
        self.refresh_customers()
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
                self.cart_table.setItem(row, 4, QTableWidgetItem(f"${item.subtotal:.2f}"))
            # Recalculate total
            self._update_total_labels()

    def change_cart_price(self, part_id, new_price: float):
        """Called when the cashier edits the unit price spinbox for a cart item."""
        if part_id in self.cart_items:
            self.cart_items[part_id].unit_price = new_price
            item = self.cart_items[part_id]
            items_list = list(self.cart_items.keys())
            if part_id in items_list:
                row = items_list.index(part_id)
                # Update subtotal column
                self.cart_table.setItem(row, 4, QTableWidgetItem(f"${item.subtotal:.2f}"))
                # Refresh the spinbox styling to reflect negotiated state
                price_spin = self.cart_table.cellWidget(row, 2)
                if isinstance(price_spin, QDoubleSpinBox):
                    is_negotiated = (item.original_unit_price is not None and
                                     abs(item.original_unit_price - new_price) > 0.001)
                    price_spin.setStyleSheet(f"""
                        QDoubleSpinBox {{
                            font-size: 12px;
                            font-weight: {'700' if is_negotiated else '500'};
                            color: {'#EA580C' if is_negotiated else '#0F172A'};
                            border: 1px solid {'#F97316' if is_negotiated else '#CBD5E1'};
                            border-radius: 4px;
                            padding: 2px 4px;
                            background: {'#FFF7ED' if is_negotiated else '#FFFFFF'};
                        }}
                        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                            width: 0; height: 0; border: none;
                        }}
                    """)
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

        # --- Resolve settlement currency ---
        sel_currency = self._get_selected_currency()
        rates = get_exchange_rates()
        exchange_rate = rates.get(sel_currency, 1.0) if sel_currency != "USD" else 1.0

        total_usd = sum(it.subtotal for it in items)
        amount_in_currency = round(total_usd * exchange_rate, 2) if sel_currency != "USD" else None

        success, result_msg = process_sale(
            cart_items=items,
            payment_method=payment_method,
            cashier_id=self.current_user.user_id,
            cashier_name=self.current_user.username,
            customer_id=customer_id,
            customer_name=customer_name,
            currency=sel_currency,
            exchange_rate=exchange_rate,
            amount_paid_curr=amount_in_currency,
        )

        if success:
            import os
            receipt_filename = os.path.basename(result_msg) if result_msg else "Receipt"
            rec_num = os.path.splitext(receipt_filename)[0]

            settings = get_all_settings()
            prt_name = settings.get("thermal_printer_name", "").strip()
            prt_info = f"Thermal receipt sent to: {prt_name}" if prt_name else "Note: You can configure a thermal receipt printer under Settings."

            equiv = get_all_currency_equivalents(total_usd)

            # Build a currency note for the success dialog
            if sel_currency == "ZAR":
                curr_note = f"Charged: <b>R {amount_in_currency:,.2f}</b>  (rate: 1 USD = {exchange_rate:.2f} ZAR)<br>"
            elif sel_currency == "ZIG":
                curr_note = f"Charged: <b>{amount_in_currency:,.2f} ZiG</b>  (rate: 1 USD = {exchange_rate:.2f} ZiG)<br>"
            else:
                curr_note = ""

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Sale Complete")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText(
                f"<b>Sale Completed Successfully!</b><br><br>"
                f"Receipt #: <b>{rec_num}</b><br>"
                f"Total (USD): <b>${total_usd:.2f}</b><br>"
                f"{curr_note}"
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
                        total_amount=total_usd,
                        payment_method=payment_method
                    )
                    open_whatsapp_chat(cust_phone, wa_msg)

            self.cart_items.clear()
            self.update_cart_display()
            self.search_input.clear()
            self.perform_search("")
        else:
            QMessageBox.critical(self, "Checkout Failed", result_msg)

