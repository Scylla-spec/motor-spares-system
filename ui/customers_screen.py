"""
Modernized Customer Management Screen for Motor Spares System.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from models.customer import Customer
from managers.customer_manager import add_customer, update_customer, get_all_customers, get_customer_purchase_history, delete_customer
from utils.validators import validate_required_name
from ui.theme import (
    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_PRIMARY_ORANGE, ScreenHeader, ICON_CUSTOMERS
)


class AddEditCustomerDialog(QDialog):
    def __init__(self, parent=None, customer=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle("Edit Customer" if customer else "Add New Customer")
        self.setMinimumWidth(400)
        self.setup_ui()
        if customer:
            self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Edit Customer" if self.customer else "Add New Customer")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full Name / Business Name")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Phone number")
        self.credit_input = QDoubleSpinBox()
        self.credit_input.setMaximum(100000)
        self.credit_input.setPrefix("$ ")

        form.addRow("Name *:", self.name_input)
        form.addRow("Phone:", self.phone_input)
        form.addRow("Credit Balance ($):", self.credit_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Customer")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 18px;
            }}
        """)
        save_btn.clicked.connect(self.save_customer)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def load_data(self):
        self.name_input.setText(self.customer.name)
        self.phone_input.setText(self.customer.phone)
        self.credit_input.setValue(self.customer.credit_balance)

    def save_customer(self):
        name = self.name_input.text().strip()
        is_valid, error = validate_required_name(name, "Customer name")
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error)
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
        self.resize(600, 380)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"Purchase History: {self.customer.name}")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        history = get_customer_purchase_history(self.customer.customer_id)

        if not history:
            no_data = QLabel("No purchase history found for this customer.")
            no_data.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-style: italic;")
            layout.addWidget(no_data)
        else:
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["SALE ID", "DATE & TIME", "AMOUNT", "PAYMENT METHOD"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setRowCount(len(history))
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.verticalHeader().setVisible(False)

            for row, sale in enumerate(history):
                table.setItem(row, 0, QTableWidgetItem(f"#{sale['sale_id']}"))
                table.setItem(row, 1, QTableWidgetItem(sale["timestamp"][:19].replace("T", " ")))
                table.setItem(row, 2, QTableWidgetItem(f"${sale['total_amount']:.2f}"))
                table.setItem(row, 3, QTableWidgetItem(sale["payment_method"]))

            layout.addWidget(table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


class CustomersScreen(QWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()
        self.load_customers()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        top_bar = QHBoxLayout()
        title_box = ScreenHeader(
            ICON_CUSTOMERS,
            "Customer Management",
            "Manage customer records, credit balances, and purchase logs.",
        )
        top_bar.addWidget(title_box)

        top_bar.addStretch()

        self.add_btn = QPushButton("+ Add New Customer")
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
            }}
        """)
        self.add_btn.clicked.connect(self.open_add_dialog)
        top_bar.addWidget(self.add_btn)
        layout.addLayout(top_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Credit Balance", "Actions"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(40)

        layout.addWidget(self.table)

    def load_customers(self):
        customers = get_all_customers()
        self.table.setRowCount(len(customers))
        for row, cust in enumerate(customers):
            id_item = QTableWidgetItem(f"#{cust.customer_id}")
            font = QFont()
            font.setBold(True)
            id_item.setFont(font)
            self.table.setItem(row, 0, id_item)

            self.table.setItem(row, 1, QTableWidgetItem(cust.name))
            self.table.setItem(row, 2, QTableWidgetItem(cust.phone or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(f"${cust.credit_balance:.2f}"))

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(8)
            action_layout.setAlignment(Qt.AlignCenter)

            edit_btn = QPushButton("Edit")
            edit_btn.setFixedHeight(28)
            edit_btn.setMinimumWidth(65)
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
            edit_btn.clicked.connect(lambda checked, c=cust: self.open_edit_dialog(c))

            history_btn = QPushButton("History")
            history_btn.setFixedHeight(28)
            history_btn.setMinimumWidth(75)
            history_btn.setCursor(Qt.PointingHandCursor)
            history_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #475569;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 2px 10px;
                }
                QPushButton:hover {
                    background-color: #F8FAFC;
                    border-color: #94A3B8;
                }
            """)
            history_btn.clicked.connect(lambda checked, c=cust: self.open_history_dialog(c))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(history_btn)

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
                del_btn.clicked.connect(lambda checked, c=cust: self.delete_customer_action(c))
                action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 4, action_widget)

    def delete_customer_action(self, customer):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete customer '{customer.name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if delete_customer(customer.customer_id):
                QMessageBox.information(self, "Success", f"Customer '{customer.name}' deleted successfully.")
                self.load_customers()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete customer.")

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
