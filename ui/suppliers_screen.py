"""
Modernized Suppliers and Purchase Orders Screen for Motor Spares System.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QComboBox, QSplitter, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from models.supplier import Supplier
from models.purchase_order import PurchaseOrder
from managers.supplier_manager import add_supplier, update_supplier, get_all_suppliers, delete_supplier
from managers.purchase_order_manager import create_po, update_po_status, get_all_pos
from utils.validators import validate_required_name
from ui.theme import (
    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_PRIMARY_ORANGE, COLOR_SUCCESS, COLOR_WARNING
)


class AddEditSupplierDialog(QDialog):
    def __init__(self, parent=None, supplier=None):
        super().__init__(parent)
        self.supplier = supplier
        self.setWindowTitle("Edit Supplier" if supplier else "Add New Supplier")
        self.setMinimumWidth(400)
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


class AddPODialog(QDialog):
    def __init__(self, suppliers, parent=None):
        super().__init__(parent)
        self.suppliers = suppliers
        self.po = None
        self.setWindowTitle("Draft Purchase Order")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Draft Purchase Order")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.supplier_combo = QComboBox()
        for sup in self.suppliers:
            self.supplier_combo.addItem(sup.name, sup.supplier_id)

        self.total_input = QDoubleSpinBox()
        self.total_input.setMaximum(1000000)
        self.total_input.setPrefix("$ ")

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Draft", "Ordered", "Received"])

        form.addRow("Supplier *:", self.supplier_combo)
        form.addRow("Total Cost Estimate ($):", self.total_input)
        form.addRow("Status:", self.status_combo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save PO")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 18px;
            }}
        """)
        save_btn.clicked.connect(self.save_po)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def save_po(self):
        if not self.suppliers:
            QMessageBox.warning(self, "Error", "No suppliers available.")
            return

        self.po = PurchaseOrder(
            po_id=None,
            supplier_id=self.supplier_combo.currentData(),
            status=self.status_combo.currentText(),
            order_date=None,
            total_cost=self.total_input.value()
        )
        self.accept()


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
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title = QLabel("Suppliers & Purchase Orders")
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {COLOR_TEXT_PRIMARY};")
        subtitle = QLabel("Manage supplier relationships and track replenishment purchase orders.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT_SECONDARY};")
        header_box.addWidget(title)
        header_box.addWidget(subtitle)
        main_layout.addLayout(header_box)

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
        po_heading = QLabel("Purchase Orders")
        po_heading.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        bottom_bar.addWidget(po_heading)
        bottom_bar.addStretch()

        self.add_po_btn = QPushButton("+ Draft New PO")
        self.add_po_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }}
        """)
        self.add_po_btn.clicked.connect(self.open_add_po)
        bottom_bar.addWidget(self.add_po_btn)
        bottom_layout.addLayout(bottom_bar)

        self.po_table = QTableWidget()
        self.po_table.setColumnCount(6)
        self.po_table.setHorizontalHeaderLabels(["PO Number", "Supplier", "Date", "Est. Total", "Status", "Actions"])
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
            num_item = QTableWidgetItem(po.po_number or str(po.po_id))
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
            action_layout.setAlignment(Qt.AlignCenter)

            if po.status != "Received":
                next_status = "Ordered" if po.status == "Draft" else "Received"
                status_btn = QPushButton(f"Mark as {next_status}")
                status_btn.setFixedHeight(28)
                status_btn.setMinimumWidth(110)
                status_btn.setCursor(Qt.PointingHandCursor)
                color = "#B45309" if next_status == "Ordered" else "#15803D"
                border = "#FCD34D" if next_status == "Ordered" else "#86EFAC"
                hover_bg = "#FEF3C7" if next_status == "Ordered" else "#F0FDF4"
                status_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #FFFFFF;
                        color: {color};
                        border: 1px solid {border};
                        border-radius: 4px;
                        font-weight: 600;
                        font-size: 12px;
                        padding: 2px 10px;
                    }}
                    QPushButton:hover {{
                        background-color: {hover_bg};
                    }}
                """)
                status_btn.clicked.connect(lambda checked, p=po, ns=next_status: self.update_po(p.po_id, ns))
                action_layout.addWidget(status_btn)

            self.po_table.setCellWidget(row, 5, action_widget)




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

        dialog = AddPODialog(self.suppliers_list, self)
        if dialog.exec():
            if create_po(dialog.po):
                self.load_pos()
            else:
                QMessageBox.critical(self, "Error", "Failed to create PO.")

    def update_po(self, po_id, next_status):
        if update_po_status(po_id, next_status):
            if next_status == "Received":
                QMessageBox.information(self, "PO Received", "PO marked as Received. Please use the Inventory 'Stock In' feature to receive individual parts into inventory.")
            self.load_pos()
        else:
            QMessageBox.critical(self, "Error", "Failed to update PO status.")
