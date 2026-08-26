"""
Modern Login Window for Motor Spares System.
Features:
- Clean modern card design with brand icon/header
- Styled input fields and prominent action button
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QWidget, QFrame
)
from PySide6.QtCore import Qt, Signal
from managers.auth_manager import authenticate_user
from ui.theme import (
    COLOR_SIDEBAR_BG, COLOR_PRIMARY_ORANGE, COLOR_PRIMARY_ORANGE_HOVER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_BORDER
)

class LoginWindow(QDialog):
    login_successful = Signal(object)  # Emits the authenticated User object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Motor Spares System - Login")
        self.setFixedSize(400, 380)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #0F172A;
            }}
        """)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 28, 24, 28)
        main_layout.setAlignment(Qt.AlignCenter)

        # Card container
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid {COLOR_BORDER};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        # Brand header inside card
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        header_layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Motor Spares System")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 800;
            color: {COLOR_TEXT_PRIMARY};
        """)
        subtitle = QLabel("Sign in to your account to continue")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"""
            font-size: 12px;
            color: {COLOR_TEXT_SECONDARY};
        """)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        card_layout.addLayout(header_layout)

        card_layout.addSpacing(6)

        # Username field
        u_label = QLabel("Username")
        u_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLOR_TEXT_PRIMARY};")
        card_layout.addWidget(u_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(36)
        card_layout.addWidget(self.username_input)

        # Password field
        p_label = QLabel("Password")
        p_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLOR_TEXT_PRIMARY};")
        card_layout.addWidget(p_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(36)
        self.password_input.returnPressed.connect(self.attempt_login)
        card_layout.addWidget(self.password_input)

        card_layout.addSpacing(6)

        # Login button
        self.login_button = QPushButton("Sign In")
        self.login_button.setFixedHeight(40)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: #FFFFFF;
                font-weight: 700;
                font-size: 14px;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_ORANGE_HOVER};
            }}
        """)
        self.login_button.clicked.connect(self.attempt_login)
        card_layout.addWidget(self.login_button)

        main_layout.addWidget(card)

    def attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Login Failed", "Please enter both username and password.")
            return
        user, message = authenticate_user(username, password)
        if user:
            self.login_successful.emit(user)
            self.accept()
        else:
            QMessageBox.critical(self, "Login Failed", message)
            self.password_input.clear()
            self.password_input.setFocus()