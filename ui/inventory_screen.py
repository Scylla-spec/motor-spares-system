"""
Modernized Inventory Management Screen for Motor Spares System.
Implements the clean ERP layout:
- Header with Title, Subtitle, KPI Stat Cards (TOTAL SKUS, TOTAL VALUE), and '+ Stock In'
- Filter bar with 'All Categories' & 'All Brands' dropdowns, search, and CSV export
- Clean table with uppercase headers, mono SKU styling, and colored pill badges for stock levels
- Pagination footer with 'Showing 1 to X of Y entries' and page buttons
"""

import csv
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QSpinBox,
    QComboBox, QFileDialog, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from models.part import Part
from models.user import User
from managers.inventory_manager import (
    get_all_parts, search_parts, add_part, update_part, record_stock_in,
    record_stock_adjustment, deactivate_part
)
from managers.supplier_manager import get_all_suppliers
from ui.excel_import_dialog import ExcelImportDialog
from ui.image_import_dialog import ImageImportDialog
from utils.validators import validate_part
from ui.theme import (
    MetricStatCard, StockBadgeDelegate, create_primary_action_button,
    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_PRIMARY_ORANGE,
    PlusMinusSpinBox, ScreenHeader, ICON_INVENTORY
)


class AddEditPartDialog(QDialog):
    def __init__(self, parent=None, part=None):
        super().__init__(parent)
        self.part = part
        self.setWindowTitle("Edit Part" if part else "Add New Part")
        self.setMinimumWidth(440)
        self._suppliers = get_all_suppliers()
        self.setup_ui()
        if part:
            self.load_part_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Edit Part" if self.part else "Add New Part")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.part_number = QLineEdit()
        self.part_number.setPlaceholderText("e.g. SKU-B849")
        self.name = QLineEdit()
        self.name.setPlaceholderText("e.g. Brake Pad Set - Front")
        self.category = QLineEdit()
        self.category.setPlaceholderText("e.g. Braking System")
        self.brand = QLineEdit()
        self.brand.setPlaceholderText("e.g. Brembo")
        self.compatible_vehicles = QLineEdit()
        self.compatible_vehicles.setPlaceholderText("e.g. Toyota Hilux, Isuzu D-Max")

        self.cost_price = QDoubleSpinBox()
        self.cost_price.setMaximum(100000)
        self.cost_price.setPrefix("$ ")
        self.cost_price.setDecimals(2)

        self.selling_price = QDoubleSpinBox()
        self.selling_price.setMaximum(100000)
        self.selling_price.setPrefix("$ ")
        self.selling_price.setDecimals(2)

        self.quantity_on_hand = QSpinBox()
        self.quantity_on_hand.setMaximum(100000)
        if self.part:
            self.quantity_on_hand.setEnabled(False)

        self.reorder_level = QSpinBox()
        self.reorder_level.setMaximum(100000)
        self.reorder_level.setValue(10)

        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("-- No Supplier --", None)
        for sup in self._suppliers:
            self.supplier_combo.addItem(sup.name, sup.supplier_id)

        form.addRow("Part Number *:", self.part_number)
        form.addRow("Name *:", self.name)
        form.addRow("Category:", self.category)
        form.addRow("Brand:", self.brand)
        form.addRow("Compatible Vehicles:", self.compatible_vehicles)
        form.addRow("Cost Price ($) *:", self.cost_price)
        form.addRow("Selling Price ($) *:", self.selling_price)
        form.addRow("Initial Quantity:", self.quantity_on_hand)
        form.addRow("Reorder Level:", self.reorder_level)
        form.addRow("Supplier:", self.supplier_combo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Part")
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 18px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
        """)
        self.save_btn.clicked.connect(self.save_part)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def load_part_data(self):
        self.part_number.setText(self.part.part_number)
        self.part_number.setEnabled(False)
        self.name.setText(self.part.name)
        self.category.setText(self.part.category)
        self.brand.setText(self.part.brand)
        self.compatible_vehicles.setText(self.part.compatible_vehicles)
        self.cost_price.setValue(self.part.cost_price)
        self.selling_price.setValue(self.part.selling_price)
        self.quantity_on_hand.setValue(self.part.quantity_on_hand)
        self.reorder_level.setValue(self.part.reorder_level)
        if self.part.supplier_id is not None:
            idx = self.supplier_combo.findData(self.part.supplier_id)
            if idx >= 0:
                self.supplier_combo.setCurrentIndex(idx)

    def save_part(self):
        is_valid, error = validate_part(
            self.part_number.text().strip(),
            self.name.text().strip(),
            self.cost_price.value(),
            self.selling_price.value(),
        )
        if not is_valid:
            QMessageBox.warning(self, "Validation", error)
            return

        new_part = Part(
            part_id=self.part.part_id if self.part else None,
            part_number=self.part_number.text().strip().upper(),
            name=self.name.text().strip().upper(),
            category=self.category.text().strip().upper(),
            brand=self.brand.text().strip().upper(),
            compatible_vehicles=self.compatible_vehicles.text().strip().upper(),
            quantity_on_hand=self.quantity_on_hand.value(),
            cost_price=self.cost_price.value(),
            selling_price=self.selling_price.value(),
            reorder_level=self.reorder_level.value(),
            supplier_id=self.supplier_combo.currentData()
        )
        self.part = new_part
        self.accept()


class QuickStockInSelectorDialog(QDialog):
    """Dialog to select a part and add incoming stock"""
    def __init__(self, parent=None, parts=None):
        super().__init__(parent)
        self.setWindowTitle("Stock In")
        self.setMinimumWidth(440)
        self.parts = parts or []
        self.selected_part = None
        self.quantity_to_add = 0
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Record Stock In")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.part_combo = QComboBox()
        for p in self.parts:
            self.part_combo.addItem(f"{p.part_number} - {p.name} (Current: {p.quantity_on_hand})", p)
        form.addRow("Select Part:", self.part_combo)

        self.quantity = PlusMinusSpinBox(1, 100000, 10)
        form.addRow("Add Quantity:", self.quantity)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("Confirm Stock In")
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 18px;
            }}
        """)
        confirm_btn.clicked.connect(self.on_confirm)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def on_confirm(self):
        self.selected_part = self.part_combo.currentData()
        self.quantity_to_add = self.quantity.value()
        if not self.selected_part:
            QMessageBox.warning(self, "Selection Required", "Please select a part.")
            return
        self.accept()


class StockInDialog(QDialog):
    def __init__(self, parent=None, part=None):
        super().__init__(parent)
        self.part = part
        self.setWindowTitle(f"Stock In: {part.name} ({part.part_number})")
        self.setMinimumWidth(380)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"Stock In: {self.part.name}")
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        curr_label = QLabel(f"Current On-Hand Stock: <b>{self.part.quantity_on_hand}</b>")
        layout.addWidget(curr_label)

        form = QFormLayout()
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 100000)
        self.quantity.setValue(1)
        form.addRow("Quantity to Add:", self.quantity)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Confirm")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }}
        """)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)


class AdjustStockDialog(QDialog):
    def __init__(self, parent=None, part=None):
        super().__init__(parent)
        self.part = part
        self.setWindowTitle(f"Adjust Stock: {part.name} ({part.part_number})")
        self.setMinimumWidth(380)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"Adjust Stock: {self.part.name}")
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        curr_label = QLabel(f"Current On-Hand Stock: <b>{self.part.quantity_on_hand}</b>")
        layout.addWidget(curr_label)

        form = QFormLayout()
        self.delta = QSpinBox()
        self.delta.setRange(-100000, 100000)
        self.delta.setValue(0)
        form.addRow("Adjustment (+/-):", self.delta)

        self.reason = QLineEdit()
        self.reason.setPlaceholderText("e.g. Physical count correction, damaged stock...")
        form.addRow("Reason *:", self.reason)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Confirm Adjustment")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }}
        """)
        save_btn.clicked.connect(self.validate_and_accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def validate_and_accept(self):
        if self.delta.value() == 0:
            QMessageBox.warning(self, "Validation Error", "Adjustment cannot be zero.")
            return
        if not self.reason.text().strip():
            QMessageBox.warning(self, "Validation Error", "A reason is required.")
            return
        self.accept()


class InventoryScreen(QWidget):
    """
    Modern Inventory Management Screen.
    Includes:
    - Page Header with KPI Stat Cards: TOTAL SKUS, TOTAL VALUE, and '+ Stock In'
    - Filters: Category and Brand dropdowns, search, CSV Export, Excel & Photo Import
    - Borderless Table with custom column sizing and colored stock pill badges
    - Pagination footer: 'Showing X to Y of Z entries' with page buttons
    """
    PAGE_SIZE = 50

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.all_active_parts = []
        self.filtered_parts = []
        self.current_page = 1

        self.setup_ui()
        self.load_inventory()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. Top Header: Title, Subtitle, Metric Cards & Primary Action
        # -------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        # Title & Subtitle
        title_box = ScreenHeader(
            ICON_INVENTORY,
            "Inventory Management",
            "Manage and track your warehouse stock.",
        )
        header_layout.addWidget(title_box)

        header_layout.addStretch()

        # KPI Metric Cards
        self.total_skus_card = MetricStatCard("TOTAL SKUS", "0")
        self.total_value_card = MetricStatCard("TOTAL VALUE", "$0.00")
        header_layout.addWidget(self.total_skus_card)
        header_layout.addWidget(self.total_value_card)

        # Primary '+ Stock In' Action Button
        self.stock_in_top_btn = create_primary_action_button("+ Stock In")
        self.stock_in_top_btn.setFixedHeight(48)
        self.stock_in_top_btn.setStyleSheet("""
            QPushButton {
                background-color: #991B1B;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 14px;
                border: none;
                border-radius: 8px;
                padding: 0px 20px;
            }
            QPushButton:hover {
                background-color: #7F1D1D;
            }
        """)
        self.stock_in_top_btn.clicked.connect(self.open_quick_stock_in)
        header_layout.addWidget(self.stock_in_top_btn)

        layout.addLayout(header_layout)

        # -------------------------------------------------------------
        # 2. Filter & Action Toolbar
        # -------------------------------------------------------------
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)

        # Filters Label
        filter_icon_label = QLabel("FILTERS:")
        filter_icon_label.setStyleSheet(f"""
            font-weight: 800;
            font-size: 11px;
            color: {COLOR_TEXT_SECONDARY};
            letter-spacing: 0.5px;
        """)
        toolbar_layout.addWidget(filter_icon_label)

        # Category Dropdown Filter
        self.category_filter = QComboBox()
        self.category_filter.setMinimumWidth(150)
        self.category_filter.addItem("All Categories", None)
        self.category_filter.currentIndexChanged.connect(self.apply_filters)
        toolbar_layout.addWidget(self.category_filter)

        # Brand Dropdown Filter
        self.brand_filter = QComboBox()
        self.brand_filter.setMinimumWidth(130)
        self.brand_filter.addItem("All Brands", None)
        self.brand_filter.currentIndexChanged.connect(self.apply_filters)
        toolbar_layout.addWidget(self.brand_filter)

        # Search Input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by SKU, name, or vehicle...")
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self.apply_filters)
        toolbar_layout.addWidget(self.search_input)

        toolbar_layout.addStretch()

        # Action Buttons on Right: + Add Part, Export CSV, Import options
        self.add_part_btn = QPushButton("+ Add Part")
        self.add_part_btn.setStyleSheet(f"""
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
        self.add_part_btn.clicked.connect(self.open_add_dialog)
        toolbar_layout.addWidget(self.add_part_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setToolTip("Export currently displayed parts to CSV file")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        toolbar_layout.addWidget(self.export_csv_btn)

        self.import_excel_btn = QPushButton("Import Excel")
        self.import_excel_btn.clicked.connect(self.open_excel_import)
        toolbar_layout.addWidget(self.import_excel_btn)

        self.import_image_btn = QPushButton("Import Photo")
        self.import_image_btn.clicked.connect(self.open_image_import)
        toolbar_layout.addWidget(self.import_image_btn)

        layout.addLayout(toolbar_layout)

        # -------------------------------------------------------------
        # 3. Modern Data Table
        # -------------------------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "#", "Part#", "Name", "Category", "Brand", "Price", "Stock", "Actions"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setItemDelegateForColumn(6, StockBadgeDelegate(self.table))
        self.table.verticalHeader().setDefaultSectionSize(40)

        layout.addWidget(self.table)

        # -------------------------------------------------------------
        # 4. Pagination / Footer Bar
        # -------------------------------------------------------------
        footer_layout = QHBoxLayout()
        
        self.footer_entries_label = QLabel("Showing 0 to 0 of 0 entries")
        self.footer_entries_label.setStyleSheet(f"""
            color: {COLOR_TEXT_SECONDARY};
            font-size: 12px;
            font-weight: 500;
        """)
        footer_layout.addWidget(self.footer_entries_label)

        footer_layout.addStretch()

        # Pagination Buttons
        self.prev_page_btn = QPushButton("<")
        self.prev_page_btn.setFixedSize(30, 30)
        self.prev_page_btn.clicked.connect(self.prev_page)
        footer_layout.addWidget(self.prev_page_btn)

        self.page_indicator_btn = QPushButton("1")
        self.page_indicator_btn.setFixedSize(30, 30)
        self.page_indicator_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_TEXT_PRIMARY};
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }}
        """)
        footer_layout.addWidget(self.page_indicator_btn)

        self.next_page_btn = QPushButton(">")
        self.next_page_btn.setFixedSize(30, 30)
        self.next_page_btn.clicked.connect(self.next_page)
        footer_layout.addWidget(self.next_page_btn)

        layout.addLayout(footer_layout)

    def load_inventory(self):
        parts = get_all_parts()
        # Filter out deactivated parts
        self.all_active_parts = [p for p in parts if not p.name.startswith("[DEACTIVATED]")]
        
        # Populate Category & Brand dropdown filters dynamically
        self._populate_filter_dropdowns()
        
        # Apply filters & display
        self.apply_filters()

    def _populate_filter_dropdowns(self):
        current_cat = self.category_filter.currentData()
        current_brand = self.brand_filter.currentData()

        categories = sorted(list(set(p.category for p in self.all_active_parts if p.category)))
        brands = sorted(list(set(p.brand for p in self.all_active_parts if p.brand)))

        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All Categories", None)
        for cat in categories:
            self.category_filter.addItem(cat, cat)
        if current_cat is not None:
            idx = self.category_filter.findData(current_cat)
            if idx >= 0:
                self.category_filter.setCurrentIndex(idx)
        self.category_filter.blockSignals(False)

        self.brand_filter.blockSignals(True)
        self.brand_filter.clear()
        self.brand_filter.addItem("All Brands", None)
        for b in brands:
            self.brand_filter.addItem(b, b)
        if current_brand is not None:
            idx = self.brand_filter.findData(current_brand)
            if idx >= 0:
                self.brand_filter.setCurrentIndex(idx)
        self.brand_filter.blockSignals(False)

    def apply_filters(self):
        query = self.search_input.text().strip().lower()
        selected_cat = self.category_filter.currentData()
        selected_brand = self.brand_filter.currentData()

        filtered = []
        for p in self.all_active_parts:
            # Category match
            if selected_cat and p.category != selected_cat:
                continue
            # Brand match
            if selected_brand and p.brand != selected_brand:
                continue
            # Search query match
            if query:
                text_corpus = f"{p.part_number} {p.name} {p.brand} {p.category} {p.compatible_vehicles}".lower()
                if query not in text_corpus:
                    continue
            filtered.append(p)

        self.filtered_parts = filtered
        self.current_page = 1
        self.update_kpi_cards()
        self.render_table_page()

    def update_kpi_cards(self):
        total_skus = len(self.all_active_parts)
        total_val = sum((p.quantity_on_hand or 0) * (p.cost_price or 0.0) for p in self.all_active_parts)

        # Format SKUs (e.g. 4,289)
        self.total_skus_card.set_value(f"{total_skus:,}")

        # Format Value (e.g. $1.24M or $12,400.00)
        if total_val >= 1_000_000:
            val_str = f"${total_val / 1_000_000:.2f}M"
        elif total_val >= 10_000:
            val_str = f"${total_val / 1_000:.1f}K"
        else:
            val_str = f"${total_val:,.2f}"
        self.total_value_card.set_value(val_str)

    PAGE_SIZE = 100

    def render_table_page(self):
        total_items = len(self.filtered_parts)
        total_pages = max(1, (total_items + self.PAGE_SIZE - 1) // self.PAGE_SIZE)

        if self.current_page > total_pages:
            self.current_page = total_pages
        if self.current_page < 1:
            self.current_page = 1

        start_idx = (self.current_page - 1) * self.PAGE_SIZE
        end_idx = min(start_idx + self.PAGE_SIZE, total_items)
        page_parts = self.filtered_parts[start_idx:end_idx]

        # Update footer text & page buttons
        if total_items == 0:
            self.footer_entries_label.setText("Showing 0 to 0 of 0 entries")
        else:
            self.footer_entries_label.setText(f"Showing {start_idx + 1} to {end_idx} of {total_items:,} entries")

        if hasattr(self, "prev_page_btn"):
            self.prev_page_btn.show()
            self.prev_page_btn.setEnabled(self.current_page > 1)
        if hasattr(self, "page_indicator_btn"):
            self.page_indicator_btn.show()
            self.page_indicator_btn.setText(f"{self.current_page} / {total_pages}")
            self.page_indicator_btn.setFixedWidth(80)
        if hasattr(self, "next_page_btn"):
            self.next_page_btn.show()
            self.next_page_btn.setEnabled(self.current_page < total_pages)

        # Render rows smoothly
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(page_parts))
            for row, part in enumerate(page_parts):
                # 0: ROW # INDEX
                row_idx_item = QTableWidgetItem(str(start_idx + row + 1))
                row_idx_item.setForeground(QColor("#64748B"))
                row_idx_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, row_idx_item)

                # 1: PART # (Bold mono-style)
                part_num_item = QTableWidgetItem(part.part_number)
                part_num_font = QFont()
                part_num_font.setBold(True)
                part_num_item.setFont(part_num_font)
                self.table.setItem(row, 1, part_num_item)

                # 2: NAME
                self.table.setItem(row, 2, QTableWidgetItem(part.name))

                # 3: CATEGORY
                self.table.setItem(row, 3, QTableWidgetItem(part.category or "—"))

                # 4: BRAND
                self.table.setItem(row, 4, QTableWidgetItem(part.brand or "—"))

                # 5: UNIT PRICE
                price_item = QTableWidgetItem(f"${part.selling_price:.2f}")
                price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 5, price_item)

                # 6: STOCK (Rendered via StockBadgeDelegate on column 6)
                stock_item = QTableWidgetItem(str(part.quantity_on_hand))
                stock_item.setData(Qt.UserRole + 1, part.is_low_stock())
                self.table.setItem(row, 6, stock_item)

                # 7: ACTIONS - Centered, professional, clean ERP styling
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(4, 2, 4, 2)
                action_layout.setSpacing(6)
                action_layout.setAlignment(Qt.AlignCenter)

                edit_btn = QPushButton("Edit")
                edit_btn.setFixedHeight(28)
                edit_btn.setMinimumWidth(56)
                edit_btn.setCursor(Qt.PointingHandCursor)
                edit_btn.setStyleSheet("""
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
                edit_btn.clicked.connect(lambda checked, p=part: self.open_edit_dialog(p))
                action_layout.addWidget(edit_btn)

                stock_in_btn = QPushButton("+ Stock")
                stock_in_btn.setFixedHeight(28)
                stock_in_btn.setMinimumWidth(68)
                stock_in_btn.setCursor(Qt.PointingHandCursor)
                stock_in_btn.setStyleSheet("""
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
                stock_in_btn.clicked.connect(lambda checked, p=part: self.open_stock_in_dialog(p))
                action_layout.addWidget(stock_in_btn)

                adjust_btn = QPushButton("Adjust")
                adjust_btn.setFixedHeight(28)
                adjust_btn.setMinimumWidth(60)
                adjust_btn.setCursor(Qt.PointingHandCursor)
                adjust_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #475569;
                        border: 1px solid #CBD5E1;
                        border-radius: 4px;
                        font-weight: 600;
                        font-size: 12px;
                        padding: 2px 8px;
                    }
                    QPushButton:hover {
                        background-color: #F8FAFC;
                        border-color: #94A3B8;
                    }
                """)
                adjust_btn.clicked.connect(lambda checked, p=part: self.open_adjust_dialog(p))
                action_layout.addWidget(adjust_btn)

                if self.current_user.is_admin():
                    del_btn = QPushButton("🗑 Delete")
                    del_btn.setFixedHeight(28)
                    del_btn.setMinimumWidth(76)
                    del_btn.setCursor(Qt.PointingHandCursor)
                    del_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #FFFFFF;
                            color: #DC2626;
                            border: 1px solid #FECACA;
                            border-radius: 4px;
                            font-weight: 600;
                            font-size: 12px;
                            padding: 2px 8px;
                        }
                        QPushButton:hover {
                            background-color: #FEF2F2;
                            border-color: #EF4444;
                        }
                    """)
                    del_btn.clicked.connect(lambda checked, p=part: self.delete_part_action(p))
                    action_layout.addWidget(del_btn)

                self.table.setCellWidget(row, 7, action_widget)
        finally:
            self.table.setUpdatesEnabled(True)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.render_table_page()

    def next_page(self):
        total_items = len(self.filtered_parts)
        total_pages = max(1, (total_items + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        if self.current_page < total_pages:
            self.current_page += 1
            self.render_table_page()

    def open_quick_stock_in(self):
        dialog = QuickStockInSelectorDialog(self, parts=self.all_active_parts)
        if dialog.exec():
            part = dialog.selected_part
            qty = dialog.quantity_to_add
            if part and qty > 0:
                success = record_stock_in(part.part_id, qty)
                if success:
                    self.load_inventory()
                    QMessageBox.information(self, "Success", f"Added {qty} units to {part.name}.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to record stock in.")

    def open_add_dialog(self):
        dialog = AddEditPartDialog(self)
        if dialog.exec():
            success = add_part(dialog.part)
            if success:
                self.load_inventory()
            else:
                QMessageBox.critical(self, "Error", "Failed to add part. Check if Part Number is unique.")

    def open_edit_dialog(self, part):
        dialog = AddEditPartDialog(self, part)
        if dialog.exec():
            success = update_part(dialog.part, self.current_user.user_id)
            if success:
                self.load_inventory()
            else:
                QMessageBox.critical(self, "Error", "Failed to update part.")

    def open_stock_in_dialog(self, part):
        dialog = StockInDialog(self, part)
        if dialog.exec():
            quantity = dialog.quantity.value()
            success = record_stock_in(part.part_id, quantity)
            if success:
                self.load_inventory()
            else:
                QMessageBox.critical(self, "Error", "Failed to record stock in.")

    def open_adjust_dialog(self, part):
        dialog = AdjustStockDialog(self, part)
        if dialog.exec():
            delta = dialog.delta.value()
            reason = dialog.reason.text().strip()
            success, message = record_stock_adjustment(
                part.part_id, delta, reason, self.current_user.user_id
            )
            if success:
                self.load_inventory()
                QMessageBox.information(self, "Stock Adjusted", message)
            else:
                QMessageBox.critical(self, "Adjustment Failed", message)

    def export_to_csv(self):
        if not self.filtered_parts:
            QMessageBox.warning(self, "Export", "No parts available to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Inventory to CSV", "inventory_export.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Part Number", "Name", "Category", "Brand", 
                    "Compatible Vehicles", "Cost Price", "Selling Price", 
                    "Stock On Hand", "Reorder Level"
                ])
                for p in self.filtered_parts:
                    writer.writerow([
                        p.part_number, p.name, p.category, p.brand,
                        p.compatible_vehicles, f"{p.cost_price:.2f}", f"{p.selling_price:.2f}",
                        p.quantity_on_hand, p.reorder_level
                    ])
            QMessageBox.information(self, "Export Complete", f"Successfully exported {len(self.filtered_parts)} parts to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Could not write CSV file:\n{str(e)}")

    def open_excel_import(self):
        dialog = ExcelImportDialog(self)
        dialog.import_complete.connect(self.load_inventory)
        dialog.exec()

    def open_image_import(self):
        dialog = ImageImportDialog(self)
        dialog.import_complete.connect(self.load_inventory)
        dialog.exec()

    def deactivate(self, part):
        confirm = QMessageBox.question(
            self, "Confirm Deactivation", 
            f"Are you sure you want to deactivate {part.part_number} - {part.name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            success = deactivate_part(part.part_id, self.current_user.user_id)
            if success:
                self.load_inventory()
            else:
                QMessageBox.critical(self, "Error", "Failed to deactivate part.")
