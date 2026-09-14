"""
Premium Login Window for Motor Spares Management System.
Full-screen split-panel design: dark branded left panel + clean right form panel.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QFont
from managers.auth_manager import authenticate_user
from utils.version import APP_VERSION_FULL, POWERED_BY
from ui.theme import ICON_X, set_btn_icon


class LoginWindow(QDialog):
    login_successful = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Motor Spares Management System")
        self.setFixedSize(820, 520)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setup_ui()

    def setup_ui(self):
        # Root layout — fills the whole window
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Outer shadow wrapper ─────────────────────────────────────────
        outer = QFrame()
        outer.setObjectName("outerShell")
        outer.setStyleSheet("""
            QFrame#outerShell {
                background-color: #FFFFFF;
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 90))
        outer.setGraphicsEffect(shadow)

        outer_layout = QHBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # ── LEFT PANEL — dark branded panel ─────────────────────────────
        left = QFrame()
        left.setFixedWidth(340)
        left.setObjectName("leftPanel")
        left.setStyleSheet("""
            QFrame#leftPanel {
                background-color: #0F172A;
                border-top-left-radius: 16px;
                border-bottom-left-radius: 16px;
            }
        """)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(36, 48, 36, 32)
        left_layout.setSpacing(0)

        # Brand mark top
        brand_mark = QLabel("MSM")
        brand_mark.setFixedSize(54, 54)
        brand_mark.setAlignment(Qt.AlignCenter)
        brand_mark.setStyleSheet("""
            background-color: #F97316;
            color: #FFFFFF;
            font-size: 22px;
            font-weight: 800;
            border-radius: 12px;
            letter-spacing: 1px;
        """)
        left_layout.addWidget(brand_mark)

        left_layout.addSpacing(28)

        # System title
        sys_title = QLabel("Motor Spares\nManagement\nSystem")
        sys_title.setStyleSheet("""
            color: #FFFFFF;
            font-size: 26px;
            font-weight: 800;
            line-height: 1.3;
            letter-spacing: -0.3px;
        """)
        left_layout.addWidget(sys_title)

        left_layout.addSpacing(16)

        # Divider line
        div = QFrame()
        div.setFixedHeight(2)
        div.setStyleSheet("background-color: #F97316; border-radius: 1px;")
        left_layout.addWidget(div)

        left_layout.addSpacing(20)

        # Tagline
        tagline = QLabel(
            "Your complete point-of-sale, inventory,\n"
            "and business management platform\n"
            "for motor spares traders."
        )
        tagline.setWordWrap(True)
        tagline.setStyleSheet("color: #64748B; font-size: 13px; line-height: 1.6;")
        left_layout.addWidget(tagline)

        left_layout.addStretch()

        # Feature bullets
        features = [
            "Point of Sale & Credit Management",
            "Live Inventory & Stock Control",
            "Thermal Receipt Printing",
            "Business Reports & Analytics",
        ]
        for feat in features:
            row = QHBoxLayout()
            row.setSpacing(10)

            dot = QLabel()
            dot.setFixedSize(7, 7)
            dot.setStyleSheet("""
                background-color: #F97316;
                border-radius: 3px;
            """)
            dot.setAlignment(Qt.AlignCenter)

            feat_lbl = QLabel(feat)
            feat_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")

            row.addWidget(dot, 0, Qt.AlignVCenter)
            row.addWidget(feat_lbl, 1)
            left_layout.addLayout(row)
            left_layout.addSpacing(8)

        left_layout.addSpacing(24)

        # Powered by — bottom of left panel
        powered_lbl = QLabel(POWERED_BY)
        powered_lbl.setStyleSheet(
            "color: #334155; font-size: 11px; font-weight: 600;"
        )
        left_layout.addWidget(powered_lbl)

        outer_layout.addWidget(left)

        # ── RIGHT PANEL — login form ─────────────────────────────────────
        right = QFrame()
        right.setObjectName("rightPanel")
        right.setStyleSheet("""
            QFrame#rightPanel {
                background-color: #FFFFFF;
                border-top-right-radius: 16px;
                border-bottom-right-radius: 16px;
            }
        """)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(48, 24, 48, 32)
        right_layout.setSpacing(0)

        # Top control bar with close button
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        close_btn = QPushButton("")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94A3B8;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #0F172A;
            }
        """)
        set_btn_icon(close_btn, ICON_X, size=14, color='#94A3B8')
        close_btn.clicked.connect(self.reject)
        top_bar.addWidget(close_btn)
        right_layout.addLayout(top_bar)

        right_layout.addSpacing(16)

        # Welcome header
        welcome = QLabel("Welcome back")
        welcome.setStyleSheet(
            "font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.3px;"
        )
        right_layout.addWidget(welcome)

        right_layout.addSpacing(6)

        sub = QLabel("Sign in to your account to continue")
        sub.setStyleSheet("font-size: 13px; color: #64748B;")
        right_layout.addWidget(sub)

        right_layout.addSpacing(36)

        # Input style shared
        field_style = """
            QLineEdit {
                background-color: #F8FAFC;
                border: 1.5px solid #E2E8F0;
                border-radius: 8px;
                font-size: 13px;
                color: #0F172A;
                padding: 0px 14px;
            }
            QLineEdit:focus {
                border-color: #F97316;
                background-color: #FFFFFF;
            }
            QLineEdit::placeholder {
                color: #94A3B8;
            }
        """

        # Username
        u_label = QLabel("Username")
        u_label.setStyleSheet(
            "font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 2px;"
        )
        right_layout.addWidget(u_label)
        right_layout.addSpacing(6)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(44)
        self.username_input.setStyleSheet(field_style)
        right_layout.addWidget(self.username_input)

        right_layout.addSpacing(18)

        # Password
        p_label = QLabel("Password")
        p_label.setStyleSheet(
            "font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 2px;"
        )
        right_layout.addWidget(p_label)
        right_layout.addSpacing(6)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(44)
        self.password_input.setStyleSheet(field_style)
        self.password_input.returnPressed.connect(self.attempt_login)
        right_layout.addWidget(self.password_input)

        right_layout.addSpacing(28)

        # Sign in button
        self.login_button = QPushButton("Sign In")
        self.login_button.setFixedHeight(46)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #F97316;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 14px;
                border: none;
                border-radius: 8px;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background-color: #EA580C;
            }
            QPushButton:pressed {
                background-color: #C2410C;
            }
        """)
        self.login_button.clicked.connect(self.attempt_login)
        right_layout.addWidget(self.login_button)

        right_layout.addStretch()

        # Version footer — bottom right
        ver_lbl = QLabel(APP_VERSION_FULL)
        ver_lbl.setAlignment(Qt.AlignRight)
        ver_lbl.setStyleSheet("font-size: 10px; color: #CBD5E1; font-weight: 600;")
        right_layout.addWidget(ver_lbl)

        outer_layout.addWidget(right)
        root.addWidget(outer)

    # ── Dragging support (frameless window) ─────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

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