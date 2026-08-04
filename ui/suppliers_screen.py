from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QComboBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from models.supplier import Supplier
from models.purchase_order import PurchaseOrder
from managers.supplier_manager import add_supplier, update_supplier, get_all_suppliers
from managers.purchase_order_manager import create_po, update_po_status, get_all_pos
from utils.validators import validate_required_name

class AddEditSupplierDialog(QDialog):
    def __init__(self, parent=None, supplier=None):
        super().__init__(parent)
        self.supplier = supplier
        self.setWindowTitle("Edit Supplier" if supplier else "Add New Supplier")
        self.setup_ui()
        if supplier:
            self.load_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.address_input = QLineEdit()
        
        layout.addRow("Name:", self.name_input)
        layout.addRow("Phone:", self.phone_input)
        layout.addRow("Address:", self.address_input)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_supplier)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

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
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.supplier_combo = QComboBox()
        for sup in self.suppliers:
            self.supplier_combo.addItem(sup.name, sup.supplier_id)
            
        self.total_input = QDoubleSpinBox()
        self.total_input.setMaximum(1000000)
        self.total_input.setPrefix("$")
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Draft", "Ordered", "Received"])
        
        layout.addRow("Supplier:", self.supplier_combo)
        layout.addRow("Total Cost Estimate:", self.total_input)
        layout.addRow("Status:", self.status_combo)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save PO")
        self.save_btn.clicked.connect(self.save_po)
        btn_layout.addWidget(self.save_btn)
        layout.addRow(btn_layout)

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
        
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # --- Top: Suppliers ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("<h3>Suppliers</h3>"))
        self.add_sup_btn = QPushButton("Add Supplier")
        self.add_sup_btn.clicked.connect(self.open_add_supplier)
        top_bar.addWidget(self.add_sup_btn, alignment=Qt.AlignRight)
        top_layout.addLayout(top_bar)
        
        self.sup_table = QTableWidget()
        self.sup_table.setColumnCount(4)
        self.sup_table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Actions"])
        self.sup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sup_table.setEditTriggers(QTableWidget.NoEditTriggers)
        top_layout.addWidget(self.sup_table)
        splitter.addWidget(top_widget)
        
        # --- Bottom: Purchase Orders ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        bottom_bar = QHBoxLayout()
        bottom_bar.addWidget(QLabel("<h3>Purchase Orders</h3>"))
        self.add_po_btn = QPushButton("Draft New PO")
        self.add_po_btn.clicked.connect(self.open_add_po)
        bottom_bar.addWidget(self.add_po_btn, alignment=Qt.AlignRight)
        bottom_layout.addLayout(bottom_bar)
        
        self.po_table = QTableWidget()
        self.po_table.setColumnCount(6)
        self.po_table.setHorizontalHeaderLabels(["PO Number", "Supplier", "Date", "Est. Total", "Status", "Actions"])
        self.po_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.po_table.setEditTriggers(QTableWidget.NoEditTriggers)
        bottom_layout.addWidget(self.po_table)
        splitter.addWidget(bottom_widget)

    def load_suppliers(self):
        self.suppliers_list = get_all_suppliers()
        self.sup_table.setRowCount(len(self.suppliers_list))
        for row, sup in enumerate(self.suppliers_list):
            self.sup_table.setItem(row, 0, QTableWidgetItem(str(sup.supplier_id)))
            self.sup_table.setItem(row, 1, QTableWidgetItem(sup.name))
            self.sup_table.setItem(row, 2, QTableWidgetItem(sup.contact_phone))
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, s=sup: self.open_edit_supplier(s))
            self.sup_table.setCellWidget(row, 3, edit_btn)

    def load_pos(self):
        pos = get_all_pos()
        self.po_table.setRowCount(len(pos))
        for row, po in enumerate(pos):
            self.po_table.setItem(row, 0, QTableWidgetItem(po.po_number or str(po.po_id)))
            self.po_table.setItem(row, 1, QTableWidgetItem(po.supplier_name))
            self.po_table.setItem(row, 2, QTableWidgetItem(str(po.order_date)))
            self.po_table.setItem(row, 3, QTableWidgetItem(f"${po.total_cost:.2f}"))
            
            status_item = QTableWidgetItem(po.status)
            if po.status == "Draft":
                status_item.setForeground(QColor("gray"))
            elif po.status == "Ordered":
                status_item.setForeground(QColor("orange"))
            elif po.status == "Received":
                status_item.setForeground(QColor("green"))
            self.po_table.setItem(row, 4, status_item)
            
            # Action to change status
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0,0,0,0)
            
            if po.status != "Received":
                next_status = "Ordered" if po.status == "Draft" else "Received"
                status_btn = QPushButton(f"Mark {next_status}")
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
