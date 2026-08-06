from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QFileDialog, QMessageBox, QGroupBox, QFormLayout
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from managers.settings_manager import get_all_settings, update_settings


class SettingsScreen(QWidget):
    """Admin-only screen for shop branding / configuration (FR-18).

    Replaces what used to be hardcoded values on the receipt (shop name,
    address, phone, footer, logo) with values an Admin can edit here.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logo_path = ""
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel("<h2>Shop Settings</h2>"))
        layout.addWidget(QLabel(
            "These values appear on printed receipts and, over time, "
            "elsewhere in the app. Changes take effect on the next receipt printed."
        ))

        group = QGroupBox("Branding")
        form = QFormLayout(group)

        self.shop_name_input = QLineEdit()
        form.addRow("Shop Name:", self.shop_name_input)

        self.address_input = QLineEdit()
        form.addRow("Address:", self.address_input)

        self.phone_input = QLineEdit()
        form.addRow("Phone:", self.phone_input)

        self.footer_input = QTextEdit()
        self.footer_input.setMaximumHeight(60)
        form.addRow("Receipt Footer:", self.footer_input)

        # --- Logo picker ---
        logo_row = QHBoxLayout()
        self.logo_preview = QLabel("No logo set")
        self.logo_preview.setFixedSize(80, 80)
        self.logo_preview.setStyleSheet("border: 1px solid #ccc; background: white;")
        self.logo_preview.setAlignment(Qt.AlignCenter)
        logo_row.addWidget(self.logo_preview)

        logo_btn_col = QVBoxLayout()
        choose_logo_btn = QPushButton("Choose Logo...")
        choose_logo_btn.clicked.connect(self.choose_logo)
        logo_btn_col.addWidget(choose_logo_btn)

        clear_logo_btn = QPushButton("Remove Logo")
        clear_logo_btn.clicked.connect(self.clear_logo)
        logo_btn_col.addWidget(clear_logo_btn)
        logo_row.addLayout(logo_btn_col)
        logo_row.addStretch()

        form.addRow("Logo:", logo_row)

        layout.addWidget(group)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 10px;"
        )
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        layout.addStretch()

    def load_settings(self):
        settings = get_all_settings()
        self.shop_name_input.setText(settings.get("shop_name", ""))
        self.address_input.setText(settings.get("address", ""))
        self.phone_input.setText(settings.get("phone", ""))
        self.footer_input.setPlainText(settings.get("receipt_footer", ""))
        self.logo_path = settings.get("logo_path", "")
        self._refresh_logo_preview()

    def _refresh_logo_preview(self):
        if self.logo_path:
            pixmap = QPixmap(self.logo_path)
            if not pixmap.isNull():
                self.logo_preview.setPixmap(
                    pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return
        self.logo_preview.setPixmap(QPixmap())
        self.logo_preview.setText("No logo set")

    def choose_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Logo Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if path:
            self.logo_path = path
            self._refresh_logo_preview()

    def clear_logo(self):
        self.logo_path = ""
        self._refresh_logo_preview()

    def save_settings(self):
        values = {
            "shop_name": self.shop_name_input.text().strip(),
            "address": self.address_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "receipt_footer": self.footer_input.toPlainText().strip(),
            "logo_path": self.logo_path,
        }
        if not values["shop_name"]:
            QMessageBox.warning(self, "Validation Error", "Shop name is required.")
            return

        if update_settings(values):
            QMessageBox.information(self, "Saved", "Shop settings updated successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")
