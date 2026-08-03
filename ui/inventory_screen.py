from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from models.part import Part
from models.user import User
from managers.inventory_manager import (
    get_all_parts, search_parts, add_part, update_part, record_stock_in,
    record_stock_adjustment, deactivate_part
)
from managers.supplier_manager import get_all_suppliers
from ui.excel_import_dialog import ExcelImportDialog

class AddEditPartDialog(QDialog):
    def __init__(self, parent=None, part=None):
        super().__init__(parent)
        self.part = part
        self.setWindowTitle("Edit Part" if part else "Add New Part")
        self.setMinimumWidth(400)
        self._suppliers = get_all_suppliers()
        self.setup_ui()
        if part:
            self.load_part_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.part_number = QLineEdit()
        self.name = QLineEdit()
        self.category = QLineEdit()
        self.brand = QLineEdit()
        self.compatible_vehicles = QLineEdit()
        
        self.cost_price = QDoubleSpinBox()
        self.cost_price.setMaximum(100000)
        self.cost_price.setPrefix("$")
        
        self.selling_price = QDoubleSpinBox()
        self.selling_price.setMaximum(100000)
        self.selling_price.setPrefix("$")
        
        self.quantity_on_hand = QSpinBox()
        self.quantity_on_hand.setMaximum(100000)
        # Quantity can only be set on creation, stock in/out handles the rest later
        if self.part:
            self.quantity_on_hand.setEnabled(False)
            
        self.reorder_level = QSpinBox()
        self.reorder_level.setMaximum(100000)
        
        # Supplier dropdown
        from PySide6.QtWidgets import QComboBox
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("-- No Supplier --", None)
        for sup in self._suppliers:
            self.supplier_combo.addItem(sup.name, sup.supplier_id)
        
        layout.addRow("Part Number:", self.part_number)
        layout.addRow("Name:", self.name)
        layout.addRow("Category:", self.category)
        layout.addRow("Brand:", self.brand)
        layout.addRow("Compatible Vehicles:", self.compatible_vehicles)
        layout.addRow("Cost Price:", self.cost_price)
        layout.addRow("Selling Price:", self.selling_price)
        layout.addRow("Initial Quantity:", self.quantity_on_hand)
        layout.addRow("Reorder Level:", self.reorder_level)
        layout.addRow("Supplier:", self.supplier_combo)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_part)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

    def load_part_data(self):
        self.part_number.setText(self.part.part_number)
        self.part_number.setEnabled(False) # Don't allow changing part number
        self.name.setText(self.part.name)
        self.category.setText(self.part.category)
        self.brand.setText(self.part.brand)
        self.compatible_vehicles.setText(self.part.compatible_vehicles)
        self.cost_price.setValue(self.part.cost_price)
        self.selling_price.setValue(self.part.selling_price)
        self.quantity_on_hand.setValue(self.part.quantity_on_hand)
        self.reorder_level.setValue(self.part.reorder_level)
        # Pre-select existing supplier
        if self.part.supplier_id is not None:
            idx = self.supplier_combo.findData(self.part.supplier_id)
            if idx >= 0:
                self.supplier_combo.setCurrentIndex(idx)

    def save_part(self):
        if not self.part_number.text().strip() or not self.name.text().strip():
            QMessageBox.warning(self, "Validation", "Part Number and Name are required.")
            return
            
        if self.selling_price.value() < self.cost_price.value():
            QMessageBox.warning(self, "Validation", "Selling price must be >= cost price.")
            return

        new_part = Part(
            part_id=self.part.part_id if self.part else None,
            part_number=self.part_number.text().strip(),
            name=self.name.text().strip(),
            category=self.category.text().strip(),
            brand=self.brand.text().strip(),
            compatible_vehicles=self.compatible_vehicles.text().strip(),
            quantity_on_hand=self.quantity_on_hand.value(),
            cost_price=self.cost_price.value(),
            selling_price=self.selling_price.value(),
            reorder_level=self.reorder_level.value(),
            supplier_id=self.supplier_combo.currentData()
        )
        
        self.part = new_part
        self.accept()

class StockInDialog(QDialog):
    def __init__(self, parent=None, part=None):
        super().__init__(parent)
        self.part = part
        self.setWindowTitle(f"Stock In: {part.name} ({part.part_number})")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"Current Stock: {self.part.quantity_on_hand}"))
        
        form = QFormLayout()
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 100000)
        form.addRow("Add Quantity:", self.quantity)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Confirm")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

class AdjustStockDialog(QDialog):
    """FR-15: manual stock adjustment, e.g. after a physical stock take."""
    def __init__(self, parent=None, part=None):
        super().__init__(parent)
        self.part = part
        self.setWindowTitle(f"Adjust Stock: {part.name} ({part.part_number})")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"Current Stock: {self.part.quantity_on_hand}"))

        form = QFormLayout()
        self.delta = QSpinBox()
        self.delta.setRange(-100000, 100000)
        self.delta.setValue(0)
        form.addRow("Adjustment (+/-):", self.delta)

        self.reason = QLineEdit()
        self.reason.setPlaceholderText("e.g. Physical count correction, damaged stock...")
        form.addRow("Reason:", self.reason)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Confirm Adjustment")
        self.save_btn.clicked.connect(self.validate_and_accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
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
    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()
        self.load_inventory()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Top Bar
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("<h3>Inventory Management</h3>"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Part Number, Name, Brand...")
        self.search_input.textChanged.connect(self.perform_search)
        top_bar.addWidget(self.search_input)
        
        self.add_btn = QPushButton("Add New Part")
        self.add_btn.clicked.connect(self.open_add_dialog)
        top_bar.addWidget(self.add_btn)
        
        self.import_btn = QPushButton("📥  Import from Excel")
        self.import_btn.clicked.connect(self.open_excel_import)
        top_bar.addWidget(self.import_btn)
        
        layout.addLayout(top_bar)
        
        # Data Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Part Number", "Name", "Category", 
            "Brand", "Stock", "Price", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table)

    def load_inventory(self, parts=None):
        if parts is None:
            parts = get_all_parts()
            
        # Filter out deactivated parts from standard view
        active_parts = [p for p in parts if not p.name.startswith("[DEACTIVATED]")]
            
        self.table.setRowCount(len(active_parts))
        for row, part in enumerate(active_parts):
            self.table.setItem(row, 0, QTableWidgetItem(str(part.part_id)))
            self.table.setItem(row, 1, QTableWidgetItem(part.part_number))
            self.table.setItem(row, 2, QTableWidgetItem(part.name))
            self.table.setItem(row, 3, QTableWidgetItem(part.category))
            self.table.setItem(row, 4, QTableWidgetItem(part.brand))
            
            stock_item = QTableWidgetItem(str(part.quantity_on_hand))
            if part.is_low_stock():
                stock_item.setBackground(QColor("#ffcccc")) # Light red
                stock_item.setForeground(QColor("black"))
            self.table.setItem(row, 5, stock_item)
            
            self.table.setItem(row, 6, QTableWidgetItem(f"${part.selling_price:.2f}"))
            
            # Action Buttons Layout
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0,0,0,0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, p=part: self.open_edit_dialog(p))
            
            stock_in_btn = QPushButton("Stock In")
            stock_in_btn.clicked.connect(lambda checked, p=part: self.open_stock_in_dialog(p))

            adjust_btn = QPushButton("Adjust Stock")
            adjust_btn.clicked.connect(lambda checked, p=part: self.open_adjust_dialog(p))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(stock_in_btn)
            action_layout.addWidget(adjust_btn)
            
            if self.current_user.is_admin():
                del_btn = QPushButton("Deactivate")
                del_btn.setStyleSheet("color: red;")
                del_btn.clicked.connect(lambda checked, p=part: self.deactivate(p))
                action_layout.addWidget(del_btn)
            
            self.table.setCellWidget(row, 7, action_widget)

    def perform_search(self, text):
        if not text.strip():
            self.load_inventory()
            return
            
        results = search_parts(text)
        self.load_inventory(results)

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
                
    def open_excel_import(self):
        dialog = ExcelImportDialog(self)
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
