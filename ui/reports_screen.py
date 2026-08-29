from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QDateEdit, QComboBox, QSpinBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from datetime import date
from managers.reports_manager import (
    get_daily_sales_summary, get_monthly_sales_summary,
    get_monthly_transactions,
    get_top_selling_parts, get_low_stock_parts, get_profit_margin_report
)
from managers.inventory_manager import record_stock_in
from managers.supplier_manager import get_all_suppliers
from managers.wishlist_manager import (
    add_wishlist_item, remove_wishlist_item, get_all_wishlist_items
)
from models.wishlist_item import WishlistItem, PRIORITY_LEVELS
from utils.reorder_export import generate_reorder_pdf
from ui.sales_trend_chart import SalesTrendChart
from ui.theme import (
    StockBadgeDelegate, COLOR_BORDER, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_PRIMARY_ORANGE, COLOR_SUCCESS,
    PlusMinusSpinBox
)

class ReportsScreen(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title = QLabel("Reports & Analytics")
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {COLOR_TEXT_PRIMARY};")
        subtitle = QLabel("Sales summaries, stock alerts, profit margins, and reorder planning.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT_SECONDARY};")
        header_box.addWidget(title)
        header_box.addWidget(subtitle)
        layout.addLayout(header_box)

        tabs = QTabWidget()
        tabs.addTab(self._build_sales_tab(), "Sales Summary")
        tabs.addTab(self._build_top_sellers_tab(), "Top Sellers")
        tabs.addTab(self._build_low_stock_tab(), "Low Stock Alert")
        tabs.addTab(self._build_margin_tab(), "Profit Margins")
        layout.addWidget(tabs)

    # ------------------------------------------------------------------ Sales Summary
    # ------------------------------------------------------------------ Sales Summary
    def _build_sales_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Controls bar
        controls = QHBoxLayout()

        # Date picker for daily report
        day_label = QLabel("Select Day:")
        day_label.setStyleSheet(f"font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        controls.addWidget(day_label)
        self.daily_date = QDateEdit(QDate.currentDate())
        self.daily_date.setCalendarPopup(True)
        self.daily_date.setDisplayFormat("yyyy-MM-dd")
        self.daily_date.dateChanged.connect(self.run_daily_report)
        controls.addWidget(self.daily_date)

        run_daily_btn = QPushButton("View Daily Report")
        run_daily_btn.clicked.connect(self.run_daily_report)
        controls.addWidget(run_daily_btn)

        month_label = QLabel("Select Month:")
        month_label.setStyleSheet(f"font-weight: 700; color: {COLOR_TEXT_PRIMARY}; margin-left: 12px;")
        controls.addWidget(month_label)
        self.month_combo = QComboBox()
        for i, m in enumerate(["January","February","March","April","May","June",
                                "July","August","September","October","November","December"], 1):
            self.month_combo.addItem(m, i)
        self.month_combo.setCurrentIndex(date.today().month - 1)

        self.year_spin = PlusMinusSpinBox(2020, 2100, date.today().year)
        controls.addWidget(self.month_combo)
        controls.addWidget(self.year_spin)

        run_monthly_btn = QPushButton("View Monthly Report")
        run_monthly_btn.clicked.connect(self.run_monthly_report)
        controls.addWidget(run_monthly_btn)
        controls.addStretch()

        layout.addLayout(controls)

        # KPI Summary Card
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        card_layout = QVBoxLayout(self.summary_card)
        card_layout.setSpacing(6)
        self.summary_title = QLabel("Sales Summary")
        self.summary_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        card_layout.addWidget(self.summary_title)

        self.summary_stats = QLabel("Select a date or month above to view transactions.")
        self.summary_stats.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT_SECONDARY};")
        card_layout.addWidget(self.summary_stats)

        self.payment_breakdown_label = QLabel("")
        self.payment_breakdown_label.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY}; padding-top: 4px;")
        card_layout.addWidget(self.payment_breakdown_label)

        layout.addWidget(self.summary_card)

        # Tabbed view for results: Daily Transactions vs Monthly Overview vs Trend
        self.sales_subtabs = QTabWidget()

        # Tab 1: Detailed Transactions List
        self.tx_tab_widget = QWidget()
        tx_layout = QVBoxLayout(self.tx_tab_widget)
        self.tx_table_header = QLabel("Transactions List:")
        self.tx_table_header.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        tx_layout.addWidget(self.tx_table_header)

        self.tx_table = self._make_table([
            "Receipt #", "Date", "Time", "Customer", "Cashier",
            "Items Purchased", "Payment", "Total Amount ($)"
        ])
        tx_layout.addWidget(self.tx_table)
        self.sales_subtabs.addTab(self.tx_tab_widget, "Transaction Details")

        # Tab 2: Monthly Day-by-Day Breakdown
        self.monthly_breakdown_widget = QWidget()
        m_layout = QVBoxLayout(self.monthly_breakdown_widget)
        hint = QLabel("Tip: Double-click any day below to view its individual transactions.")
        hint.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-style: italic;")
        m_layout.addWidget(hint)

        self.daily_breakdown_table = self._make_table([
            "Date", "Transactions", "Cash ($)", "EcoCash ($)", "Card ($)", "Total Revenue ($)"
        ])
        self.daily_breakdown_table.cellDoubleClicked.connect(self._on_monthly_day_clicked)
        m_layout.addWidget(self.daily_breakdown_table)
        self.sales_subtabs.addTab(self.monthly_breakdown_widget, "Monthly Day-by-Day Breakdown")

        # Tab 3: Sales Trend Graph (FR-22)
        self.chart_tab_widget = QWidget()
        chart_layout = QVBoxLayout(self.chart_tab_widget)
        chart_title = QLabel("Revenue Trend (Daily):")
        chart_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        chart_layout.addWidget(chart_title)
        self.sales_chart = SalesTrendChart()
        chart_layout.addWidget(self.sales_chart)
        self.sales_subtabs.addTab(self.chart_tab_widget, "Sales Trend Graph")

        layout.addWidget(self.sales_subtabs)

        # Run initial report for today
        self.run_daily_report()

        return w

    def run_daily_report(self):
        d = self.daily_date.date().toString("yyyy-MM-dd")
        result = get_daily_sales_summary(d)

        total_rev = result["total_revenue"]
        tx_count = result["transaction_count"]
        cash_rev = result["cash_revenue"]
        eco_rev = result["ecocash_revenue"]
        card_rev = result["card_revenue"]
        txs = result.get("transactions", [])

        self.summary_title.setText(f"Daily Sales Report: {d}")
        self.summary_stats.setText(
            f"Total Cash/Revenue Earned: ${total_rev:.2f}   |   "
            f"Total Transactions: {tx_count}   |   "
            f"Total Items Sold: {result.get('total_items', 0)}"
        )
        self.payment_breakdown_label.setText(
            f"Payment Breakdown:  Cash: ${cash_rev:.2f}   |   "
            f"EcoCash: ${eco_rev:.2f}   |   "
            f"Card: ${card_rev:.2f}"
        )

        self.tx_table_header.setText(f"Every Transaction on {d} ({len(txs)} total):")
        self._populate_transactions_table(txs, show_date=False)

        # Clear monthly breakdown table when running a single day
        self.daily_breakdown_table.setRowCount(0)

        # Switch to transaction details tab
        self.sales_subtabs.setCurrentIndex(0)

    def run_monthly_report(self):
        year = self.year_spin.value()
        month = self.month_combo.currentData()
        month_name = self.month_combo.currentText()

        day_rows = get_monthly_sales_summary(year, month)
        all_txs = get_monthly_transactions(year, month)

        total_rev = sum(r["total_revenue"] for r in day_rows)
        total_tx = sum(r["transaction_count"] for r in day_rows)
        cash_rev = sum(r.get("cash_revenue", 0) for r in day_rows)
        eco_rev = sum(r.get("ecocash_revenue", 0) for r in day_rows)
        card_rev = sum(r.get("card_revenue", 0) for r in day_rows)

        self.summary_title.setText(f"Monthly Sales Report: {month_name} {year}")
        self.summary_stats.setText(
            f"Total Cash/Revenue Earned: ${total_rev:.2f}   |   "
            f"Total Transactions: {total_tx}   |   "
            f"Days with Sales: {len(day_rows)}"
        )
        self.payment_breakdown_label.setText(
            f"Payment Breakdown:  Cash: ${cash_rev:.2f}   |   "
            f"EcoCash: ${eco_rev:.2f}   |   "
            f"Card: ${card_rev:.2f}"
        )

        # 1. Populate all individual transactions in the month
        self.tx_table_header.setText(f"Every Transaction in {month_name} {year} ({len(all_txs)} total):")
        self._populate_transactions_table(all_txs, show_date=True)

        # 2. Populate day-by-day summary
        self.daily_breakdown_table.setRowCount(len(day_rows))
        for i, r in enumerate(day_rows):
            self.daily_breakdown_table.setItem(i, 0, QTableWidgetItem(r["date"]))
            self.daily_breakdown_table.setItem(i, 1, QTableWidgetItem(str(r["transaction_count"])))
            self.daily_breakdown_table.setItem(i, 2, QTableWidgetItem(f"${r.get('cash_revenue', 0):.2f}"))
            self.daily_breakdown_table.setItem(i, 3, QTableWidgetItem(f"${r.get('ecocash_revenue', 0):.2f}"))
            self.daily_breakdown_table.setItem(i, 4, QTableWidgetItem(f"${r.get('card_revenue', 0):.2f}"))
            self.daily_breakdown_table.setItem(i, 5, QTableWidgetItem(f"${r['total_revenue']:.2f}"))

        # 3. Update Chart
        self.sales_chart.update_chart(day_rows, f"{month_name} {year}")

        # Switch to day-by-day or transactions
        self.sales_subtabs.setCurrentIndex(0)

    def _populate_transactions_table(self, transactions, show_date=True):
        """Helper to display detailed transactions in the table."""
        self.tx_table.setRowCount(len(transactions))
        for row, tx in enumerate(transactions):
            date_display = tx.get("date", tx.get("timestamp", "")[:10]) if show_date else "-"
            self.tx_table.setItem(row, 0, QTableWidgetItem(tx["receipt_no"]))
            self.tx_table.setItem(row, 1, QTableWidgetItem(date_display))
            self.tx_table.setItem(row, 2, QTableWidgetItem(tx["time"]))
            self.tx_table.setItem(row, 3, QTableWidgetItem(tx["customer_name"]))
            self.tx_table.setItem(row, 4, QTableWidgetItem(tx["cashier_name"]))
            self.tx_table.setItem(row, 5, QTableWidgetItem(tx["items_summary"]))

            # Payment method styling
            pay_item = QTableWidgetItem(tx["payment_method"])
            if tx["payment_method"] == "Cash":
                pay_item.setForeground(QColor(COLOR_SUCCESS))
            elif tx["payment_method"] == "EcoCash":
                pay_item.setForeground(QColor("#0284C7"))
            elif tx["payment_method"] == "Card":
                pay_item.setForeground(QColor("#7C3AED"))
            self.tx_table.setItem(row, 6, pay_item)

            amount_item = QTableWidgetItem(f"${tx['total_amount']:.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tx_table.setItem(row, 7, amount_item)

    def _on_monthly_day_clicked(self, row, col):
        """When a user double-clicks a day in the monthly table, drill down into that day."""
        date_item = self.daily_breakdown_table.item(row, 0)
        if date_item:
            day_str = date_item.text().strip()
            qdate = QDate.fromString(day_str, "yyyy-MM-dd")
            if qdate.isValid():
                self.daily_date.setDate(qdate)
                self.run_daily_report()

    # ------------------------------------------------------------------ Top Sellers
    def _build_top_sellers_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Top"))
        self.top_limit = PlusMinusSpinBox(5, 50, 10)
        top_bar.addWidget(self.top_limit)
        top_bar.addWidget(QLabel("best-selling parts"))
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_top_sellers)
        top_bar.addWidget(refresh_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.top_table = self._make_table(
            ["Part #", "Name", "Brand", "Category", "Qty Sold", "Revenue ($)"]
        )
        layout.addWidget(self.top_table)
        self.load_top_sellers()
        return w

    def load_top_sellers(self):
        data = get_top_selling_parts(self.top_limit.value())
        self.top_table.setRowCount(len(data))
        for i, r in enumerate(data):
            self.top_table.setItem(i, 0, QTableWidgetItem(r["part_number"]))
            self.top_table.setItem(i, 1, QTableWidgetItem(r["name"]))
            self.top_table.setItem(i, 2, QTableWidgetItem(r["brand"]))
            self.top_table.setItem(i, 3, QTableWidgetItem(r["category"]))
            qty_item = QTableWidgetItem(str(r["total_qty_sold"]))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.top_table.setItem(i, 4, qty_item)
            rev_item = QTableWidgetItem(f"${r['total_revenue']:.2f}")
            rev_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.top_table.setItem(i, 5, rev_item)

    # ------------------------------------------------------------------ Low Stock
    def _build_low_stock_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Parts at or below their reorder level:"))
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_low_stock)
        top_bar.addWidget(refresh_btn)

        export_btn = QPushButton("Export Reorder List (PDF)")
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
        """)
        export_btn.clicked.connect(self.export_reorder_list)
        top_bar.addWidget(export_btn)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.low_stock_table = self._make_table(
            ["Part #", "Name", "Brand", "Category", "On Hand", "Reorder Level", "Shortage", "Action"]
        )
        self.low_stock_table.setItemDelegateForColumn(4, StockBadgeDelegate(self.low_stock_table))
        layout.addWidget(self.low_stock_table)
        self.load_low_stock()

        # --- Reorder Wishlist section (FR-21) ---
        # Manually-added items for parts that are unavailable or not yet
        # catalogued, so they don't get missed on the next supplier visit.
        wishlist_heading = QLabel("Reorder Wishlist \u2014 unavailable or uncatalogued items:")
        wishlist_heading.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(wishlist_heading)

        wishlist_bar = QHBoxLayout()
        add_wishlist_btn = QPushButton("Add Wishlist Item")
        add_wishlist_btn.clicked.connect(self.add_wishlist_item_dialog)
        wishlist_bar.addWidget(add_wishlist_btn)
        wishlist_bar.addStretch()
        layout.addLayout(wishlist_bar)

        self.wishlist_table = self._make_table(
            ["Description", "Priority", "Preferred Supplier", "Notes", "Date Added", "Action"]
        )
        layout.addWidget(self.wishlist_table)
        self.load_wishlist()

        return w

    def load_wishlist(self):
        data = get_all_wishlist_items()
        self.wishlist_table.setRowCount(len(data))
        priority_colors = {"High": "#f8d7da", "Medium": "#fff3cd", "Low": "#e2e3e5"}
        for i, r in enumerate(data):
            self.wishlist_table.setItem(i, 0, QTableWidgetItem(r["description"]))

            priority_item = QTableWidgetItem(r["priority"])
            priority_item.setBackground(QColor(priority_colors.get(r["priority"], "#ffffff")))
            priority_item.setTextAlignment(Qt.AlignCenter)
            self.wishlist_table.setItem(i, 1, priority_item)

            self.wishlist_table.setItem(i, 2, QTableWidgetItem(r["supplier_name"] or "\u2014"))
            self.wishlist_table.setItem(i, 3, QTableWidgetItem(r["notes"] or ""))
            self.wishlist_table.setItem(i, 4, QTableWidgetItem(str(r["date_added"])))

            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda checked, wid=r["wishlist_id"]: self.remove_wishlist_item_confirm(wid))
            self.wishlist_table.setCellWidget(i, 5, remove_btn)

    def add_wishlist_item_dialog(self):
        from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Reorder Wishlist Item")
        form = QFormLayout(dialog)

        desc_input = QLineEdit()
        form.addRow("Description:", desc_input)

        priority_input = QComboBox()
        priority_input.addItems(PRIORITY_LEVELS)
        priority_input.setCurrentText("Medium")
        form.addRow("Priority:", priority_input)

        supplier_input = QComboBox()
        supplier_input.addItem("(None)", None)
        for s in get_all_suppliers():
            supplier_input.addItem(s.name, s.supplier_id)
        form.addRow("Preferred Supplier:", supplier_input)

        notes_input = QTextEdit()
        notes_input.setMaximumHeight(60)
        form.addRow("Notes:", notes_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            description = desc_input.text().strip()
            if not description:
                QMessageBox.warning(self, "Validation Error", "Description is required.")
                return
            item = WishlistItem(
                wishlist_id=None,
                description=description,
                preferred_supplier_id=supplier_input.currentData(),
                priority=priority_input.currentText(),
                notes=notes_input.toPlainText().strip(),
                date_added=None,
                added_by=None
            )
            if add_wishlist_item(item, added_by=self.current_user.user_id):
                self.load_wishlist()
            else:
                QMessageBox.critical(self, "Error", "Failed to add wishlist item.")

    def remove_wishlist_item_confirm(self, wishlist_id):
        from PySide6.QtWidgets import QMessageBox as MB
        reply = MB.question(
            self, "Remove Wishlist Item",
            "Remove this item from the reorder wishlist?",
            MB.Yes | MB.No
        )
        if reply == MB.Yes:
            if remove_wishlist_item(wishlist_id):
                self.load_wishlist()

    def load_low_stock(self):
        data = get_low_stock_parts()
        self.low_stock_table.setRowCount(len(data))
        for i, r in enumerate(data):
            self.low_stock_table.setItem(i, 0, QTableWidgetItem(r["part_number"]))
            self.low_stock_table.setItem(i, 1, QTableWidgetItem(r["name"]))
            self.low_stock_table.setItem(i, 2, QTableWidgetItem(r["brand"]))
            self.low_stock_table.setItem(i, 3, QTableWidgetItem(r["category"]))

            qty_item = QTableWidgetItem(str(r["quantity_on_hand"]))
            qty_item.setData(Qt.UserRole + 1, True)
            self.low_stock_table.setItem(i, 4, qty_item)

            self.low_stock_table.setItem(i, 5, QTableWidgetItem(str(r["reorder_level"])))

            short_item = QTableWidgetItem(str(r["shortage"]))
            short_item.setForeground(QColor("red"))
            short_item.setTextAlignment(Qt.AlignCenter)
            self.low_stock_table.setItem(i, 6, short_item)

            stock_btn = QPushButton("Quick Stock In")
            stock_btn.clicked.connect(lambda checked, pid=r["part_id"], name=r["name"], short=r["shortage"]:
                                      self.quick_stock_in(pid, name, short))
            self.low_stock_table.setCellWidget(i, 7, stock_btn)

    def quick_stock_in(self, part_id, name, shortage):
        from PySide6.QtWidgets import QInputDialog
        suggested = max(1, int(shortage)) if shortage else 1
        qty, ok = QInputDialog.getInt(
            self,
            "Quick Stock In",
            f"Add stock for {name}:\n(Suggested: {suggested} to reach reorder level)",
            suggested,
            1,
            100000,
            1
        )
        if ok and qty > 0:
            if record_stock_in(part_id, qty):
                self.load_low_stock()

    def export_reorder_list(self):
        data = get_low_stock_parts()
        wishlist_data = get_all_wishlist_items()
        filepath = generate_reorder_pdf(data, wishlist_data)
        if filepath:
            QMessageBox.information(
                self, "Reorder List Exported",
                f"Reorder list saved to:\n{filepath}"
            )
        else:
            QMessageBox.critical(self, "Export Failed", "Could not generate the reorder list PDF.")

    # ------------------------------------------------------------------ Profit Margin
    def _build_margin_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Profit margin per part (based on actual sales):"))
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_margins)
        top_bar.addWidget(refresh_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.margin_table = self._make_table(
            ["Part #", "Name", "Brand", "Cost ($)", "Sell ($)", "Qty Sold",
             "Revenue ($)", "COGS ($)", "Gross Profit ($)", "Margin %"]
        )
        layout.addWidget(self.margin_table)
        self.load_margins()
        return w

    def load_margins(self):
        data = get_profit_margin_report()
        self.margin_table.setRowCount(len(data))
        for i, r in enumerate(data):
            self.margin_table.setItem(i, 0, QTableWidgetItem(r["part_number"]))
            self.margin_table.setItem(i, 1, QTableWidgetItem(r["name"]))
            self.margin_table.setItem(i, 2, QTableWidgetItem(r["brand"]))
            self.margin_table.setItem(i, 3, QTableWidgetItem(f"${r['cost_price']:.2f}"))
            self.margin_table.setItem(i, 4, QTableWidgetItem(f"${r['selling_price']:.2f}"))
            self.margin_table.setItem(i, 5, QTableWidgetItem(str(r["total_sold"])))
            self.margin_table.setItem(i, 6, QTableWidgetItem(f"${r['total_revenue']:.2f}"))
            self.margin_table.setItem(i, 7, QTableWidgetItem(f"${r['total_cogs']:.2f}"))
            self.margin_table.setItem(i, 8, QTableWidgetItem(f"${r['gross_profit']:.2f}"))

            margin_item = QTableWidgetItem(f"{r['margin_pct']:.1f}%")
            margin_item.setTextAlignment(Qt.AlignCenter)
            if r["margin_pct"] >= 20:
                margin_item.setForeground(QColor("green"))
            elif r["margin_pct"] >= 0:
                margin_item.setForeground(QColor("orange"))
            else:
                margin_item.setForeground(QColor("red"))
            self.margin_table.setItem(i, 9, margin_item)

    # ------------------------------------------------------------------ Helper
    def _make_table(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.verticalHeader().setVisible(False)
        return t
