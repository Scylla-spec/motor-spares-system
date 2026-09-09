"""
Modernized Suppliers and Purchase Orders Screen for Motor Spares System.
Features full procurement workflow:
- Itemized Purchase Order creation with searchable parts picker
- 1-Click Auto-Fill for low stock items
- 1-Click "Receive & Stock In" to update warehouse inventory automatically
- Official Branded PO PDF Export
- Itemized PO breakdown viewer
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QSpinBox,
    QComboBox, QSplitter, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from models.supplier import Supplier
from models.purchase_order import PurchaseOrder
from managers.supplier_manager import add_supplier, update_supplier, get_all_suppliers, delete_supplier
from managers.purchase_order_manager import (
    create_po_with_items, receive_po_stock, get_all_pos, get_po_by_id,
    get_low_stock_parts_for_reorder
)
from managers.inventory_manager import get_all_parts
from utils.validators import validate_required_name
from utils.po_export import generate_po_pdf
from ui.theme import (
    MetricStatCard, create_orange_button, StockBadgeDelegate,
    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_PRIMARY_ORANGE, COLOR_SUCCESS, ScreenHeader, ICON_SUPPLIERS, COLOR_WARNING,
    set_btn_icon, ICON_PDF, ICON_ZAPPER, ICON_DOWNLOAD
)


class AddEditSupplierDialog(QDialog):
    def __init__(self, parent=None, supplier=None):
        super().__init__(parent)
        self.supplier = supplier
        self.setWindowTitle("Edit Supplier" if supplier else "Add New Supplier")
        self.setMinimumWidth(420)
        self.setup_ui()
        if supplier:
            self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Edit Supplier" if self.supplier else "Add New Supplier")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Supplier / Vendor Company Name")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Contact Phone")
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Business Address")

        form.addRow("Name *:", self.name_input)
        form.addRow("Phone:", self.phone_input)
        form.addRow("Address:", self.address_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Supplier")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 18px;
            }}
        """)
        save_btn.clicked.connect(self.save_supplier)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def load_data(self):
        self.name_input.setText(self.supplier.name)
        self.phone_input.setText(self.supplier.contact_phone)
        self.address_input.setText(self.supplier.address)

    def save_supplier(self):
        name = self.name_input.text().strip()
        is_valid, error = validate_required_name(name, "Supplier name")
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error)
            return

        self.supplier = Supplier(
            supplier_id=self.supplier.supplier_id if self.supplier else None,
            name=name,
            contact_phone=self.phone_input.text().strip(),
            address=self.address_input.text().strip()
        )
        self.accept()


class ViewPOItemsDialog(QDialog):
    """Dialog showing the itemized parts, quantities, and costs for a Purchase Order."""
    def __init__(self, po: PurchaseOrder, parent=None):
        super().__init__(parent)
        self.po = po
        self.setWindowTitle(f"Purchase Order {po.po_number or f'#{po.po_id}'} Details")
        self.resize(680, 440)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"Purchase Order {self.po.po_number or f'#{self.po_id}'}")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        info_label = QLabel(
            f"Supplier: <b>{self.po.supplier_name}</b> | Date: <b>{self.po.order_date or '—'}</b> | "
            f"Status: <b>{self.po.status}</b> | Total: <b>${self.po.total_cost:.2f}</b>"
        )
        info_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(info_label)

        # Line items table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Part#", "Part Name", "Qty Ordered", "Unit Cost", "Subtotal"])
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        items = self.po.items or []
        table.setRowCount(len(items))
        for row, it in enumerate(items):
            pnum_item = QTableWidgetItem(it.part_number)
            font = QFont()
            font.setBold(True)
            pnum_item.setFont(font)
            table.setItem(row, 0, pnum_item)
            table.setItem(row, 1, QTableWidgetItem(it.part_name))
            table.setItem(row, 2, QTableWidgetItem(str(it.quantity_ordered)))
            table.setItem(row, 3, QTableWidgetItem(f"${it.unit_cost:.2f}"))
            table.setItem(row, 4, QTableWidgetItem(f"${it.subtotal:.2f}"))

        layout.addWidget(table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        export_btn = QPushButton("Export PO PDF")
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_PRIMARY_ORANGE};
                border: 1px solid {COLOR_PRIMARY_ORANGE};
                border-radius: 4px;
                font-weight: 600;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: #FFF7ED;
            }}
        """)
        export_btn.clicked.connect(self._export_pdf)
        set_btn_icon(export_btn, ICON_PDF, size=14, color=COLOR_PRIMARY_ORANGE)
        btn_layout.addWidget(export_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _export_pdf(self):
        pdf_path = generate_po_pdf(self.po)
        if pdf_path:
            QMessageBox.information(self, "PDF Exported", f"Purchase Order PDF successfully created:\n{pdf_path}")
            try:
                os.startfile(pdf_path)
            except Exception:
                pass
        else:
            QMessageBox.critical(self, "Error", "Failed to generate Purchase Order PDF.")


class AddPODialog(QDialog):
    """Full-featured Purchase Order creation dialog with itemized parts and low-stock autofill."""
    def __init__(self, suppliers, parent=None, prefill_low_stock=False):
        super().__init__(parent)
        self.suppliers = suppliers
        self.prefill_low_stock = prefill_low_stock
        self._all_parts = [p for p in get_all_parts() if not p.name.startswith("[DEACTIVATED]")]
        self._filtered_parts = list(self._all_parts)
        self.items_list = []  # list of dicts

        self.setWindowTitle("Draft New Purchase Order")
        self.resize(740, 580)
        self.setup_ui()

        if self.prefill_low_stock:
            self._autofill_low_stock()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Draft Official Purchase Order")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        # Supplier & Status Form
        top_form = QFormLayout()
        top_form.setSpacing(8)

        self.supplier_combo = QComboBox()
        for sup in self.suppliers:
            self.supplier_combo.addItem(f"{sup.name} ({sup.contact_phone or 'No phone'})", sup.supplier_id)
        top_form.addRow("Target Supplier *:", self.supplier_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Ordered", "Draft"])
        top_form.addRow("Order Status:", self.status_combo)

        layout.addLayout(top_form)

        # --- Items Section ---
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

        item_hdr_row = QHBoxLayout()
        item_hdr = QLabel("Search & Add Parts to Order:")
        item_hdr.setStyleSheet(f"font-weight: 700; font-size: 12px; color: {COLOR_TEXT_PRIMARY};")
        item_hdr_row.addWidget(item_hdr)

        item_hdr_row.addStretch()

        autofill_btn = QPushButton("Auto-Fill Low Stock Parts")
        autofill_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEF3C7;
                color: #B45309;
                border: 1px solid #FCD34D;
                border-radius: 4px;
                font-weight: 700;
                font-size: 11px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #FDE68A;
            }
        """)
        autofill_btn.clicked.connect(self._autofill_low_stock)
        set_btn_icon(autofill_btn, ICON_ZAPPER, size=13, color='#B45309')
        item_hdr_row.addWidget(autofill_btn)
        item_layout.addLayout(item_hdr_row)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by part number, name, brand, or vehicle...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        item_layout.addWidget(self.search_input)

        # Add item row
        add_row = QHBoxLayout()
        add_row.setSpacing(8)

        self.part_combo = QComboBox()
        self.part_combo.setMinimumWidth(280)
        self.part_combo.currentIndexChanged.connect(self._on_part_selection_changed)
        add_row.addWidget(self.part_combo, 3)

        cost_label = QLabel("Cost:")
        cost_label.setStyleSheet("font-size: 11px; font-weight: 600;")
        add_row.addWidget(cost_label)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setMaximum(1000000)
        self.cost_spin.setPrefix("$ ")
        self.cost_spin.setDecimals(2)
        self.cost_spin.setFixedWidth(85)
        self.cost_spin.setToolTip("Unit Purchase Cost")
        add_row.addWidget(self.cost_spin)

        qty_label = QLabel("Qty:")
        qty_label.setStyleSheet("font-size: 11px; font-weight: 600;")
        add_row.addWidget(qty_label)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 10000)
        self.qty_spin.setValue(10)
        self.qty_spin.setFixedWidth(70)
        self.qty_spin.setToolTip("Quantity to order")
        add_row.addWidget(self.qty_spin)

        add_part_btn = QPushButton("+ Add to PO")
        add_part_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
        """)
        add_part_btn.clicked.connect(self._add_part_to_po)
        add_row.addWidget(add_part_btn)

        item_layout.addLayout(add_row)
        layout.addWidget(item_box)

        # Initial parts populate
        self._populate_parts_combo()

        # Selected items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(["Part#", "Part Name", "Qty", "Unit Cost", "Subtotal", "Action"])
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

        # Total label
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.total_label = QLabel("Total Order Cost: $0.00")
        self.total_label.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {COLOR_TEXT_PRIMARY};")
        bottom_row.addWidget(self.total_label)
        layout.addLayout(bottom_row)

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Create Purchase Order")
        save_btn.setStyleSheet(f"""
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
        save_btn.clicked.connect(self._create_po)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _populate_parts_combo(self):
        self.part_combo.blockSignals(True)
        self.part_combo.clear()
        if not self._filtered_parts:
            self.part_combo.addItem("-- No matching parts found --", None)
            self.part_combo.setEnabled(False)
        else:
            self.part_combo.setEnabled(True)
            for p in self._filtered_parts:
                self.part_combo.addItem(
                    f"{p.part_number} — {p.name} (On Hand: {p.quantity_on_hand}, Cost: ${p.cost_price:.2f})",
                    p.part_id
                )
        self.part_combo.blockSignals(False)
        self._on_part_selection_changed(0)

    def _on_search_text_changed(self, text: str):
        query = text.strip().lower()
        if not query:
            self._filtered_parts = list(self._all_parts)
        else:
            self._filtered_parts = [
                p for p in self._all_parts
                if query in (p.part_number or "").lower()
                or query in (p.name or "").lower()
                or query in (p.brand or "").lower()
                or query in (p.category or "").lower()
                or query in (p.compatible_vehicles or "").lower()
            ]
        self._populate_parts_combo()

    def _on_part_selection_changed(self, index: int):
        part_id = self.part_combo.currentData()
        if not part_id:
            return
        part = next((p for p in self._all_parts if p.part_id == part_id), None)
        if part:
            self.cost_spin.setValue(part.cost_price)

    def _add_part_to_po(self):
        part_id = self.part_combo.currentData()
        if not part_id:
            return
        part = next((p for p in self._all_parts if p.part_id == part_id), None)
        if not part:
            return

        qty = self.qty_spin.value()
        cost = self.cost_spin.value()

        existing = next((it for it in self.items_list if it["part_id"] == part_id), None)
        if existing:
            existing["quantity_ordered"] += qty
            existing["unit_cost"] = cost
        else:
            self.items_list.append({
                "part_id": part.part_id,
                "part_number": part.part_number,
                "part_name": part.name,
                "quantity_ordered": qty,
                "unit_cost": cost
            })

        self._refresh_table()
        self.search_input.selectAll()
        self.search_input.setFocus()

    def _autofill_low_stock(self):
        low_stock = get_low_stock_parts_for_reorder()
        if not low_stock:
            QMessageBox.information(self, "Stock Healthy", "No parts are currently at or below their reorder level.")
            return

        count_added = 0
        for item in low_stock:
            part_id = item["part_id"]
            existing = next((it for it in self.items_list if it["part_id"] == part_id), None)
            if not existing:
                self.items_list.append({
                    "part_id": item["part_id"],
                    "part_number": item["part_number"],
                    "part_name": item["name"],
                    "quantity_ordered": item["suggested_qty"],
                    "unit_cost": item["cost_price"]
                })
                count_added += 1

        self._refresh_table()
        QMessageBox.information(self, "Low Stock Added", f"Added {count_added} low-stock parts with suggested quantities into this PO.")

    def _refresh_table(self):
        self.items_table.setRowCount(len(self.items_list))
        total = 0.0
        for row, it in enumerate(self.items_list):
            subtotal = it["quantity_ordered"] * it["unit_cost"]
            pnum_item = QTableWidgetItem(it["part_number"])
            font = QFont()
            font.setBold(True)
            pnum_item.setFont(font)
            self.items_table.setItem(row, 0, pnum_item)
            self.items_table.setItem(row, 1, QTableWidgetItem(it["part_name"]))
            self.items_table.setItem(row, 2, QTableWidgetItem(str(it["quantity_ordered"])))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"${it['unit_cost']:.2f}"))
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

        self.total_label.setText(f"Total Order Cost: ${total:.2f}")

    def _remove_item(self, idx):
        if 0 <= idx < len(self.items_list):
            self.items_list.pop(idx)
            self._refresh_table()

    def _create_po(self):
        if not self.suppliers:
            QMessageBox.warning(self, "Error", "No suppliers available.")
            return
        if not self.items_list:
            QMessageBox.warning(self, "Validation Error", "Please add at least one part to order.")
            return

        supplier_id = self.supplier_combo.currentData()
        status = self.status_combo.currentText()

        ok, msg, po_id = create_po_with_items(supplier_id, self.items_list, status)
        if ok:
            QMessageBox.information(self, "Success", f"Purchase Order {msg} created successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", f"Failed to create purchase order: {msg}")


class SuppliersScreen(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()
        self.load_suppliers()
        self.load_pos()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header
        main_layout.addWidget(ScreenHeader(
            ICON_SUPPLIERS,
            "Suppliers & Purchase Orders",
            "Manage supplier relationships, draft itemized purchase orders, and receive incoming inventory stock.",
        ))

        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet("QSplitter::handle { background-color: #E2E8F0; height: 2px; }")
        main_layout.addWidget(splitter)

        # --- Top: Suppliers ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 8)
        top_layout.setSpacing(10)

        top_bar = QHBoxLayout()
        sup_heading = QLabel("Suppliers Directory")
        sup_heading.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        top_bar.addWidget(sup_heading)
        top_bar.addStretch()

        self.add_sup_btn = QPushButton("+ Add Supplier")
        self.add_sup_btn.setStyleSheet(f"""
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
        self.add_sup_btn.clicked.connect(self.open_add_supplier)
        top_bar.addWidget(self.add_sup_btn)
        top_layout.addLayout(top_bar)

        self.sup_table = QTableWidget()
        self.sup_table.setColumnCount(4)
        self.sup_table.setHorizontalHeaderLabels(["ID", "Name", "Contact Phone", "Actions"])
        sup_hdr = self.sup_table.horizontalHeader()
        sup_hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        sup_hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        sup_hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        sup_hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.sup_table.verticalHeader().setVisible(False)
        self.sup_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sup_table.setEditTriggers(QTableWidget.NoEditTriggers)
        top_layout.addWidget(self.sup_table)
        splitter.addWidget(top_widget)

        # --- Bottom: Purchase Orders ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 8, 0, 0)
        bottom_layout.setSpacing(10)

        bottom_bar = QHBoxLayout()
        po_heading = QLabel("Purchase Orders & Stock Replenishment")
        po_heading.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        bottom_bar.addWidget(po_heading)
        bottom_bar.addStretch()

        self.reorder_low_btn = QPushButton("Auto-Order Low Stock")
        self.reorder_low_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEF3C7;
                color: #B45309;
                border: 1px solid #FCD34D;
                border-radius: 6px;
                font-weight: 700;
                font-size: 12px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #FDE68A;
            }
        """)
        self.reorder_low_btn.clicked.connect(self.open_auto_reorder_po)
        set_btn_icon(self.reorder_low_btn, ICON_ZAPPER, size=14, color='#B45309')
        bottom_bar.addWidget(self.reorder_low_btn)

        self.add_po_btn = QPushButton("+ Draft New PO")
        self.add_po_btn.setStyleSheet(f"""
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
        self.add_po_btn.clicked.connect(self.open_add_po)
        bottom_bar.addWidget(self.add_po_btn)
        bottom_layout.addLayout(bottom_bar)

        self.po_table = QTableWidget()
        self.po_table.setColumnCount(6)
        self.po_table.setHorizontalHeaderLabels(["PO Number", "Supplier", "Date", "Total Cost", "Status", "Actions"])
        po_hdr = self.po_table.horizontalHeader()
        po_hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        po_hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        po_hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        po_hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        po_hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        po_hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.po_table.verticalHeader().setVisible(False)
        self.po_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.po_table.setEditTriggers(QTableWidget.NoEditTriggers)
        bottom_layout.addWidget(self.po_table)
        splitter.addWidget(bottom_widget)

    def load_suppliers(self):
        self.suppliers_list = get_all_suppliers()
        self.sup_table.setRowCount(len(self.suppliers_list))
        self.sup_table.verticalHeader().setDefaultSectionSize(40)
        for row, sup in enumerate(self.suppliers_list):
            id_item = QTableWidgetItem(f"#{sup.supplier_id}")
            font = QFont()
            font.setBold(True)
            id_item.setFont(font)
            self.sup_table.setItem(row, 0, id_item)

            self.sup_table.setItem(row, 1, QTableWidgetItem(sup.name))
            self.sup_table.setItem(row, 2, QTableWidgetItem(sup.contact_phone or "—"))

            edit_widget = QWidget()
            edit_layout = QHBoxLayout(edit_widget)
            edit_layout.setContentsMargins(4, 2, 4, 2)
            edit_layout.setAlignment(Qt.AlignCenter)

            edit_btn = QPushButton("Edit")
            edit_btn.setFixedHeight(28)
            edit_btn.setMinimumWidth(70)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #0F172A;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 2px 10px;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                    border-color: #94A3B8;
                }
            """)
            edit_btn.clicked.connect(lambda checked, s=sup: self.open_edit_supplier(s))
            edit_layout.addWidget(edit_btn)

            if self.current_user and self.current_user.is_admin():
                del_btn = QPushButton("Delete")
                del_btn.setFixedHeight(28)
                del_btn.setMinimumWidth(65)
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #EF4444;
                        font-weight: 700;
                        font-size: 12px;
                        border: 1px solid #FECACA;
                        border-radius: 4px;
                        padding: 2px 8px;
                    }
                    QPushButton:hover {
                        background-color: #FEF2F2;
                        border-color: #EF4444;
                    }
                """)
                del_btn.clicked.connect(lambda checked, s=sup: self.delete_supplier_action(s))
                edit_layout.addWidget(del_btn)

            self.sup_table.setCellWidget(row, 3, edit_widget)

    def delete_supplier_action(self, supplier):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete supplier '{supplier.name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if delete_supplier(supplier.supplier_id):
                QMessageBox.information(self, "Success", f"Supplier '{supplier.name}' deleted successfully.")
                self.load_suppliers()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete supplier.")

    def load_pos(self):
        pos = get_all_pos()
        self.po_table.setRowCount(len(pos))
        self.po_table.verticalHeader().setDefaultSectionSize(40)
        for row, po in enumerate(pos):
            num_item = QTableWidgetItem(po.po_number or f"PO-#{po.po_id}")
            font = QFont()
            font.setBold(True)
            num_item.setFont(font)
            self.po_table.setItem(row, 0, num_item)

            self.po_table.setItem(row, 1, QTableWidgetItem(po.supplier_name))
            self.po_table.setItem(row, 2, QTableWidgetItem(str(po.order_date or "—")))
            self.po_table.setItem(row, 3, QTableWidgetItem(f"${po.total_cost:.2f}"))

            # Status chip
            status_item = QTableWidgetItem(po.status)
            if po.status == "Draft":
                status_item.setForeground(QColor("#64748B"))
            elif po.status == "Ordered":
                status_item.setForeground(QColor("#D97706"))
            elif po.status == "Received":
                status_item.setForeground(QColor("#16A34A"))
            self.po_table.setItem(row, 4, status_item)

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignCenter)

            # 1. View Items button
            view_btn = QPushButton("View Items")
            view_btn.setFixedHeight(28)
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #0F172A;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                }
            """)
            view_btn.clicked.connect(lambda checked, p_id=po.po_id: self.open_view_po(p_id))
            action_layout.addWidget(view_btn)

            pdf_btn = QPushButton("PDF")
            pdf_btn.setFixedHeight(28)
            pdf_btn.setCursor(Qt.PointingHandCursor)
            pdf_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #475569;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background-color: #F8FAFC;
                    color: #F97316;
                    border-color: #F97316;
                }
            """)
            pdf_btn.clicked.connect(lambda checked, p_id=po.po_id: self.export_po_pdf_action(p_id))
            set_btn_icon(pdf_btn, ICON_PDF, size=13, color='#475569')
            action_layout.addWidget(pdf_btn)

            if po.status != "Received":
                receive_btn = QPushButton("Receive & Stock In")
                receive_btn.setFixedHeight(28)
                receive_btn.setCursor(Qt.PointingHandCursor)
                receive_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F0FDF4;
                        color: #15803D;
                        border: 1px solid #86EFAC;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 2px 10px;
                    }
                    QPushButton:hover {
                        background-color: #DCFCE7;
                        border-color: #4ADE80;
                    }
                """)
                receive_btn.clicked.connect(lambda checked, p_id=po.po_id: self.receive_po_action(p_id))
                set_btn_icon(receive_btn, ICON_DOWNLOAD, size=13, color='#15803D')
                action_layout.addWidget(receive_btn)

            self.po_table.setCellWidget(row, 5, action_widget)

    def open_view_po(self, po_id: int):
        po = get_po_by_id(po_id)
        if not po:
            QMessageBox.warning(self, "Error", "Could not load purchase order details.")
            return
        dialog = ViewPOItemsDialog(po, self)
        dialog.exec()

    def export_po_pdf_action(self, po_id: int):
        po = get_po_by_id(po_id)
        if not po:
            QMessageBox.warning(self, "Error", "Could not load purchase order details.")
            return
        pdf_path = generate_po_pdf(po)
        if pdf_path:
            QMessageBox.information(self, "PDF Exported", f"Purchase Order PDF saved to:\n{pdf_path}")
            try:
                os.startfile(pdf_path)
            except Exception:
                pass
        else:
            QMessageBox.critical(self, "Error", "Failed to generate Purchase Order PDF.")

    def receive_po_action(self, po_id: int):
        po = get_po_by_id(po_id)
        po_name = po.po_number if po else f"#{po_id}"
        reply = QMessageBox.question(
            self, "Confirm Stock In",
            f"Receive shipment for Purchase Order {po_name}?\n\n"
            f"This will automatically increment your warehouse inventory quantities for all items on this order and record stock movements.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            ok, msg = receive_po_stock(po_id)
            if ok:
                QMessageBox.information(self, "Stock Received", msg)
                self.load_pos()
            else:
                QMessageBox.critical(self, "Receive Failed", msg)

    def open_add_supplier(self):
        dialog = AddEditSupplierDialog(self)
        if dialog.exec():
            if add_supplier(dialog.supplier):
                self.load_suppliers()
            else:
                QMessageBox.critical(self, "Error", "Failed to add supplier.")

    def open_edit_supplier(self, supplier):
        dialog = AddEditSupplierDialog(self, supplier)
        if dialog.exec():
            if update_supplier(dialog.supplier):
                self.load_suppliers()
            else:
                QMessageBox.critical(self, "Error", "Failed to update supplier.")

    def open_add_po(self):
        if not self.suppliers_list:
            QMessageBox.warning(self, "No Suppliers", "Please add a supplier first.")
            return

        dialog = AddPODialog(self.suppliers_list, self, prefill_low_stock=False)
        if dialog.exec():
            self.load_pos()

    def open_auto_reorder_po(self):
        if not self.suppliers_list:
            QMessageBox.warning(self, "No Suppliers", "Please add a supplier first.")
            return

        dialog = AddPODialog(self.suppliers_list, self, prefill_low_stock=True)
        if dialog.exec():
            self.load_pos()
