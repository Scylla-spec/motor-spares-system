from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QDateEdit, QComboBox, QSplitter, QSpinBox, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from datetime import date
from managers.reports_manager import (
    get_daily_sales_summary, get_monthly_sales_summary,
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

class ReportsScreen(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>Reports & Analytics</h3>"))

        tabs = QTabWidget()
        tabs.addTab(self._build_sales_tab(), "Sales Summary")
        tabs.addTab(self._build_top_sellers_tab(), "Top Sellers")
        tabs.addTab(self._build_low_stock_tab(), "Low Stock Alert")
        tabs.addTab(self._build_margin_tab(), "Profit Margins")
        layout.addWidget(tabs)

    # ------------------------------------------------------------------ Sales Summary
    def _build_sales_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        controls = QHBoxLayout()

        # Date picker for daily
        controls.addWidget(QLabel("Daily report for:"))
        self.daily_date = QDateEdit(QDate.currentDate())
        self.daily_date.setCalendarPopup(True)
        controls.addWidget(self.daily_date)

        run_daily_btn = QPushButton("Run Daily")
        run_daily_btn.clicked.connect(self.run_daily_report)
        controls.addWidget(run_daily_btn)

        controls.addWidget(QLabel("  |  Monthly report:"))
        self.month_combo = QComboBox()
        for i, m in enumerate(["January","February","March","April","May","June",
                                "July","August","September","October","November","December"], 1):
            self.month_combo.addItem(m, i)
        self.month_combo.setCurrentIndex(date.today().month - 1)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(2020, 2100)
        self.year_spin.setValue(date.today().year)
        controls.addWidget(self.month_combo)
        controls.addWidget(self.year_spin)

        run_monthly_btn = QPushButton("Run Monthly")
        run_monthly_btn.clicked.connect(self.run_monthly_report)
        controls.addWidget(run_monthly_btn)
        controls.addStretch()

        layout.addLayout(controls)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-size: 14px; padding: 6px;")
        layout.addWidget(self.summary_label)

        self.sales_table = self._make_table(["Date", "Transactions", "Revenue ($)"])
        layout.addWidget(self.sales_table)

        # --- Sales Trend Graph (FR-22) ---
        layout.addWidget(QLabel("<b>Sales Trend</b> (updates when you run a monthly report):"))
        self.sales_chart = SalesTrendChart()
        layout.addWidget(self.sales_chart)

        return w

    def run_daily_report(self):
        d = self.daily_date.date().toString("yyyy-MM-dd")
        result = get_daily_sales_summary(d)
        self.summary_label.setText(
            f"<b>{d}</b>  |  Transactions: {result['transaction_count']}  |  "
            f"Total Revenue: <b>${result['total_revenue']:.2f}</b>"
        )
        self.sales_table.setRowCount(1)
        self.sales_table.setItem(0, 0, QTableWidgetItem(d))
        self.sales_table.setItem(0, 1, QTableWidgetItem(str(result["transaction_count"])))
        self.sales_table.setItem(0, 2, QTableWidgetItem(f"${result['total_revenue']:.2f}"))

    def run_monthly_report(self):
        year = self.year_spin.value()
        month = self.month_combo.currentData()
        rows = get_monthly_sales_summary(year, month)

        total_rev = sum(r["total_revenue"] for r in rows)
        total_tx = sum(r["transaction_count"] for r in rows)
        month_name = self.month_combo.currentText()
        self.summary_label.setText(
            f"<b>{month_name} {year}</b>  |  Transactions: {total_tx}  |  "
            f"Total Revenue: <b>${total_rev:.2f}</b>"
        )
        self.sales_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.sales_table.setItem(i, 0, QTableWidgetItem(r["date"]))
            self.sales_table.setItem(i, 1, QTableWidgetItem(str(r["transaction_count"])))
            self.sales_table.setItem(i, 2, QTableWidgetItem(f"${r['total_revenue']:.2f}"))

        self.sales_chart.update_chart(rows, f"{month_name} {year}")

    # ------------------------------------------------------------------ Top Sellers
    def _build_top_sellers_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Top"))
        self.top_limit = QSpinBox()
        self.top_limit.setRange(5, 50)
        self.top_limit.setValue(10)
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
        export_btn.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 6px;")
        export_btn.clicked.connect(self.export_reorder_list)
        top_bar.addWidget(export_btn)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.low_stock_table = self._make_table(
            ["Part #", "Name", "Brand", "Category", "On Hand", "Reorder Level", "Shortage", "Action"]
        )
        layout.addWidget(self.low_stock_table)
        self.load_low_stock()

        # --- Reorder Wishlist section (FR-21) ---
        # Manually-added items for parts that are unavailable or not yet
        # catalogued, so they don't get missed on the next supplier visit.
        layout.addWidget(QLabel("<b>Reorder Wishlist</b> \u2014 unavailable or uncatalogued items:"))

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
            qty_item.setBackground(QColor("#f8d7da"))
            qty_item.setTextAlignment(Qt.AlignCenter)
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
        qty, ok = QInputDialog.getInt(
            self, "Quick Stock In",
            f"Add stock for {name}:\n(Suggested: {shortage} to reach reorder level)",
            value=shortage, min=1, max=100000
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
        return t
