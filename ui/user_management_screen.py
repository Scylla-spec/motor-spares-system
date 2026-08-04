from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from managers.auth_manager import get_all_users, create_user
from managers.backup_manager import backup_database
from utils.validators import validate_new_user

class UserManagementScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_users()

    def setup_ui(self):
        layout = QHBoxLayout(self)

        # Left panel: User List
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("<h3>System Users</h3>"))
        
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(4)
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Role", "Password Hash"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        left_layout.addWidget(self.user_table)

        self.backup_btn = QPushButton("Back Up Database")
        self.backup_btn.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px;")
        self.backup_btn.clicked.connect(self.run_backup)
        left_layout.addWidget(self.backup_btn)

        layout.addLayout(left_layout, 2)  # Give table more space

        # Right panel: Add User Form
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("<h3>Add New User</h3>"))
        
        right_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        right_layout.addWidget(self.username_input)
        
        right_layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        right_layout.addWidget(self.password_input)
        
        right_layout.addWidget(QLabel("Role:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Cashier", "Admin"])
        right_layout.addWidget(self.role_combo)
        
        self.add_user_btn = QPushButton("Create User")
        self.add_user_btn.clicked.connect(self.add_user)
        right_layout.addWidget(self.add_user_btn)
        
        right_layout.addStretch()  # Push fields to top
        layout.addLayout(right_layout, 1)

    def load_users(self):
        users = get_all_users()
        self.user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            self.user_table.setItem(row, 0, QTableWidgetItem(str(user.user_id)))
            self.user_table.setItem(row, 1, QTableWidgetItem(user.username))
            self.user_table.setItem(row, 2, QTableWidgetItem(user.role))
            self.user_table.setItem(row, 3, QTableWidgetItem(user.password_hash[:15] + "..."))

    def run_backup(self):
        success, result = backup_database()
        if success:
            QMessageBox.information(
                self, "Backup Complete",
                f"Database backed up successfully to:\n{result}"
            )
        else:
            QMessageBox.critical(self, "Backup Failed", result)

    def add_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        role = self.role_combo.currentText()
        
        is_valid, error = validate_new_user(username, password)
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error)
            return
            
        success = create_user(username, password, role)
        if success:
            QMessageBox.information(self, "Success", f"User '{username}' created successfully.")
            self.username_input.clear()
            self.password_input.clear()
            self.load_users()  # Refresh table
        else:
            QMessageBox.critical(self, "Error", "Failed to create user. Username might already exist.")