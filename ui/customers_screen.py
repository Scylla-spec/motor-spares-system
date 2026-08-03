from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDoubleSpinBox
)
from PySide6.QtCore import Qt
from models.customer import Customer
from managers.customer_manager import add_customer, update_customer, get_all_customers, get_customer_purchase_history

class AddEditCustomerDialog(QDialog):
    def __init__(self, parent=None, customer=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle("Edit Customer" if customer else "Add New Customer")
        self.setup_ui()
        if customer:
            self.load_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.credit_input = QDoubleSpinBox()
        self.credit_input.setMaximum(100000)
        self.credit_input.setPrefix("$")
        
        layout.addRow("Name:", self.name_input)
        layout.addRow("Phone:", self.phone_input)
        layout.addRow("Credit Balance:", self.credit_input)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_customer)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

    def load_data(self):
        self.name_input.setText(self.customer.name)
        self.phone_input.setText(self.customer.phone)
        self.credit_input.setValue(self.customer.credit_balance)

    def save_customer(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Name is required.")
            return
            
        self.customer = Customer(
            customer_id=self.customer.customer_id if self.customer else None,
            name=name,
            phone=self.phone_input.text().strip(),
            credit_balance=self.credit_input.value()
        )
        self.accept()


class PurchaseHistoryDialog(QDialog):
    def __init__(self, customer, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle(f"Purchase History - {customer.name}")
        self.resize(500, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        history = get_customer_purchase_history(self.customer.customer_id)
        
        if not history:
            layout.addWidget(QLabel("No purchase history found for this customer."))
            return
            
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Sale ID", "Date", "Amount", "Payment"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setRowCount(len(history))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        for row, sale in enumerate(history):
            table.setItem(row, 0, QTableWidgetItem(str(sale["sale_id"])))
            table.setItem(row, 1, QTableWidgetItem(sale["timestamp"][:19].replace("T", " ")))
            table.setItem(row, 2, QTableWidgetItem(f"${sale['total_amount']:.2f}"))
            table.setItem(row, 3, QTableWidgetItem(sale["payment_method"]))
            
        layout.addWidget(table)


class CustomersScreen(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()
        self.load_customers()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("<h3>Customer Management</h3>"))
        
        self.add_btn = QPushButton("Add New Customer")
        self.add_btn.clicked.connect(self.open_add_dialog)
        top_bar.addWidget(self.add_btn, alignment=Qt.AlignRight)
        layout.addLayout(top_bar)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Credit Balance", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table)

    def load_customers(self):
        customers = get_all_customers()
        self.table.setRowCount(len(customers))
        for row, cust in enumerate(customers):
            self.table.setItem(row, 0, QTableWidgetItem(str(cust.customer_id)))
            self.table.setItem(row, 1, QTableWidgetItem(cust.name))
            self.table.setItem(row, 2, QTableWidgetItem(cust.phone))
            self.table.setItem(row, 3, QTableWidgetItem(f"${cust.credit_balance:.2f}"))
            
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0,0,0,0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, c=cust: self.open_edit_dialog(c))
            
            history_btn = QPushButton("View History")
            history_btn.clicked.connect(lambda checked, c=cust: self.open_history_dialog(c))
            
            action_layout.addWidget(edit_btn)
            action_layout.addWidget(history_btn)
            
            self.table.setCellWidget(row, 4, action_widget)

    def open_add_dialog(self):
        dialog = AddEditCustomerDialog(self)
        if dialog.exec():
            if add_customer(dialog.customer):
                self.load_customers()
            else:
                QMessageBox.critical(self, "Error", "Failed to add customer.")

    def open_edit_dialog(self, customer):
        dialog = AddEditCustomerDialog(self, customer)
        if dialog.exec():
            if update_customer(dialog.customer):
                self.load_customers()
            else:
                QMessageBox.critical(self, "Error", "Failed to update customer.")
                
    def open_history_dialog(self, customer):
        dialog = PurchaseHistoryDialog(customer, self)
        dialog.exec()
