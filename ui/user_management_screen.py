from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFrame, QFormLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from managers.auth_manager import get_all_users, create_user, delete_user
from managers.backup_manager import backup_database
from utils.validators import validate_new_user
from ui.theme import (
    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_PRIMARY_ORANGE
)


class UserManagementScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_users()

    def setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title = QLabel("User Management")
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {COLOR_TEXT_PRIMARY};")
        subtitle = QLabel("Manage system users, roles, and database backups.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT_SECONDARY};")
        header_box.addWidget(title)
        header_box.addWidget(subtitle)
        outer.addLayout(header_box)

        layout = QHBoxLayout()
        layout.setSpacing(16)

        # Left panel: User List
        left_card = QFrame()
        left_card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
            }}
        """)
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        users_heading = QLabel("System Users")
        users_heading.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        left_layout.addWidget(users_heading)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Role", "Password Hash", "Action"])
        u_header = self.user_table.horizontalHeader()
        u_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        u_header.setSectionResizeMode(1, QHeaderView.Stretch)
        u_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        u_header.setSectionResizeMode(3, QHeaderView.Stretch)
        u_header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.user_table.setColumnWidth(4, 110)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.verticalHeader().setDefaultSectionSize(40)
        left_layout.addWidget(self.user_table)

        self.backup_btn = QPushButton("Back Up Database")
        self.backup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 14px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
        """)
        self.backup_btn.clicked.connect(self.run_backup)
        left_layout.addWidget(self.backup_btn)

        layout.addWidget(left_card, 2)

        # Right panel: Add User Form
        right_card = QFrame()
        right_card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
            }}
        """)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        add_heading = QLabel("Add New User")
        add_heading.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        right_layout.addWidget(add_heading)

        form = QFormLayout()
        form.setSpacing(10)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        form.addRow("Username:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter password")
        form.addRow("Password:", self.password_input)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Cashier", "Admin"])
        form.addRow("Role:", self.role_combo)

        right_layout.addLayout(form)

        self.add_user_btn = QPushButton("Create User")
        self.add_user_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 14px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
        """)
        self.add_user_btn.clicked.connect(self.add_user)
        right_layout.addWidget(self.add_user_btn)

        right_layout.addStretch()
        layout.addWidget(right_card, 1)

        outer.addLayout(layout)

    def load_users(self):
        users = get_all_users()
        self.user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            id_item = QTableWidgetItem(str(user.user_id))
            font = QFont()
            font.setBold(True)
            id_item.setFont(font)
            self.user_table.setItem(row, 0, id_item)
            self.user_table.setItem(row, 1, QTableWidgetItem(user.username))
            self.user_table.setItem(row, 2, QTableWidgetItem(user.role))
            self.user_table.setItem(row, 3, QTableWidgetItem(user.password_hash[:15] + "..."))

            del_widget = QWidget()
            del_layout = QHBoxLayout(del_widget)
            del_layout.setContentsMargins(4, 2, 4, 2)
            del_layout.setAlignment(Qt.AlignCenter)

            del_btn = QPushButton("Delete")
            del_btn.setFixedSize(88, 30)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #EF4444;
                    font-weight: 700;
                    font-size: 11px;
                    border: 1px solid #FECACA;
                    border-radius: 4px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #FEF2F2;
                    border-color: #EF4444;
                }
            """)
            del_btn.clicked.connect(lambda checked, u=user: self.on_delete_user(u))
            del_layout.addWidget(del_btn)
            self.user_table.setCellWidget(row, 4, del_widget)

    def on_delete_user(self, user):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete user '{user.username}' (ID: {user.user_id})?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, msg = delete_user(user.user_id)
            if success:
                QMessageBox.information(self, "Success", msg)
                self.load_users()
            else:
                QMessageBox.warning(self, "Delete Failed", msg)

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
            self.load_users()
        else:
            QMessageBox.critical(self, "Error", "Failed to create user. Username might already exist.")
