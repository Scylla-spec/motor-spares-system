from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QFileDialog, QMessageBox, QFrame, QFormLayout,
    QComboBox, QCheckBox, QScrollArea
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from managers.settings_manager import get_all_settings, update_settings
from utils.thermal_receipt import get_available_printers, test_print_thermal_receipt
from ui.theme import (
    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_PRIMARY_ORANGE,
    ScreenHeader, ICON_SETTINGS
)


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
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        layout.addWidget(ScreenHeader(
            ICON_SETTINGS,
            "Shop Settings",
            "These values appear on printed receipts and, over time, "
            "elsewhere in the app. Changes take effect on the next receipt printed.",
        ))

        group = QFrame()
        group.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)

        branding_title = QLabel("Branding")
        branding_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        group_layout.addWidget(branding_title)

        form = QFormLayout()
        form.setSpacing(10)

        self.shop_name_input = QLineEdit()
        form.addRow("Shop Name:", self.shop_name_input)

        self.address_input = QLineEdit()
        form.addRow("Address:", self.address_input)

        self.phone_input = QLineEdit()
        form.addRow("Phone:", self.phone_input)

        self.footer_input = QTextEdit()
        self.footer_input.setMaximumHeight(60)
        form.addRow("Receipt Footer:", self.footer_input)

        logo_row = QHBoxLayout()
        self.logo_preview = QLabel("No logo set")
        self.logo_preview.setFixedSize(80, 80)
        self.logo_preview.setStyleSheet(f"border: 1px solid {COLOR_BORDER}; background: white; border-radius: 6px;")
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
        group_layout.addLayout(form)
        layout.addWidget(group)

        # Thermal Receipt Machine Configuration Card
        printer_group = QFrame()
        printer_group.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        p_layout = QVBoxLayout(printer_group)
        p_layout.setSpacing(12)

        printer_title = QLabel("Receipt Machine (Thermal ESC/POS)")
        printer_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        p_layout.addWidget(printer_title)

        printer_subtitle = QLabel(
            "Configure your supermarket-style thermal receipt printer (e.g. Epson, Xprinter, POS-80, POS-58). "
            "Receipts will be printed on standard narrow rolls instead of A4 pages."
        )
        printer_subtitle.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY};")
        printer_subtitle.setWordWrap(True)
        p_layout.addWidget(printer_subtitle)

        p_form = QFormLayout()
        p_form.setSpacing(10)

        # Printer selector row
        printer_row = QHBoxLayout()
        self.printer_combo = QComboBox()
        self.printer_combo.setMinimumWidth(300)
        printer_row.addWidget(self.printer_combo, 1)

        refresh_prt_btn = QPushButton("⟳ Refresh")
        refresh_prt_btn.setToolTip("Scan for newly plugged-in USB receipt printers")
        refresh_prt_btn.setFixedHeight(30)
        refresh_prt_btn.clicked.connect(self.populate_printers)
        printer_row.addWidget(refresh_prt_btn)
        p_form.addRow("Printer Device:", printer_row)

        # Paper width selector
        self.paper_width_combo = QComboBox()
        self.paper_width_combo.addItem("80mm (Standard Supermarket Roll - Recommended)", "80")
        self.paper_width_combo.addItem("58mm (Small Compact POS Roll)", "58")
        p_form.addRow("Paper Width:", self.paper_width_combo)

        # Options checkboxes
        self.auto_print_check = QCheckBox("Automatically print receipt immediately after completing checkout in POS")
        self.auto_print_check.setChecked(True)
        p_form.addRow("Auto-Print:", self.auto_print_check)

        self.cut_paper_check = QCheckBox("Automatically feed paper and cut roll at the end of the receipt")
        self.cut_paper_check.setChecked(True)
        p_form.addRow("Paper Cut:", self.cut_paper_check)

        # Test Print button row
        test_row = QHBoxLayout()
        self.test_print_btn = QPushButton("🖨 Test Print Receipt")
        self.test_print_btn.setFixedHeight(34)
        self.test_print_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-weight: 600;
                padding: 0px 14px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                border-color: #94A3B8;
            }
        """)
        self.test_print_btn.clicked.connect(self.handle_test_print)
        test_row.addWidget(self.test_print_btn)

        self.test_status_label = QLabel("")
        self.test_status_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        test_row.addWidget(self.test_status_label)
        test_row.addStretch()

        p_form.addRow("Test Hardware:", test_row)
        p_layout.addLayout(p_form)
        layout.addWidget(printer_group)

        # Multi-Currency & WhatsApp Configuration Card
        currency_group = QFrame()
        currency_group.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        c_layout = QVBoxLayout(currency_group)
        c_layout.setSpacing(12)

        currency_title = QLabel("Multi-Currency & WhatsApp Direct (Southern Africa POS)")
        currency_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        c_layout.addWidget(currency_title)

        currency_subtitle = QLabel(
            "Configure daily counter exchange rates and default messaging country code. "
            "The POS cart dynamically computes live ZiG and ZAR totals and change."
        )
        currency_subtitle.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY};")
        currency_subtitle.setWordWrap(True)
        c_layout.addWidget(currency_subtitle)

        c_form = QFormLayout()
        c_form.setSpacing(10)

        self.rate_zig_input = QLineEdit()
        self.rate_zig_input.setPlaceholderText("e.g. 26.50")
        c_form.addRow("USD to ZiG Rate (1 USD = X ZiG):", self.rate_zig_input)

        self.rate_zar_input = QLineEdit()
        self.rate_zar_input.setPlaceholderText("e.g. 18.20")
        c_form.addRow("USD to ZAR Rate (1 USD = X ZAR):", self.rate_zar_input)

        self.phone_prefix_input = QLineEdit()
        self.phone_prefix_input.setPlaceholderText("+263")
        c_form.addRow("WhatsApp Country Code:", self.phone_prefix_input)

        c_layout.addLayout(c_form)
        layout.addWidget(currency_group)

        self.save_btn = QPushButton("Save All Settings")
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 18px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
        """)
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        layout.addStretch()

    def populate_printers(self):
        current_selection = self.printer_combo.currentText()
        self.printer_combo.clear()
        self.printer_combo.addItem("-- Select Thermal Receipt Printer --", "")
        printers = get_available_printers()
        for p in printers:
            self.printer_combo.addItem(p, p)

        # Try restoring previous selection
        idx = self.printer_combo.findText(current_selection)
        if idx >= 0:
            self.printer_combo.setCurrentIndex(idx)

    def load_settings(self):
        self.populate_printers()
        settings = get_all_settings()
        self.shop_name_input.setText(settings.get("shop_name", ""))
        self.address_input.setText(settings.get("address", ""))
        self.phone_input.setText(settings.get("phone", ""))
        self.footer_input.setPlainText(settings.get("receipt_footer", ""))
        self.logo_path = settings.get("logo_path", "")
        self._refresh_logo_preview()

        # Load thermal printer settings
        saved_printer = settings.get("thermal_printer_name", "")
        if saved_printer:
            idx = self.printer_combo.findData(saved_printer)
            if idx >= 0:
                self.printer_combo.setCurrentIndex(idx)
            else:
                self.printer_combo.addItem(saved_printer, saved_printer)
                self.printer_combo.setCurrentIndex(self.printer_combo.count() - 1)

        saved_width = settings.get("thermal_paper_width", "80")
        w_idx = self.paper_width_combo.findData(saved_width)
        if w_idx >= 0:
            self.paper_width_combo.setCurrentIndex(w_idx)

        self.auto_print_check.setChecked(settings.get("thermal_auto_print", "1") == "1")
        self.cut_paper_check.setChecked(settings.get("thermal_cut_paper", "1") == "1")

        # Load currency and phone settings
        self.rate_zig_input.setText(settings.get("rate_zig", "26.50"))
        self.rate_zar_input.setText(settings.get("rate_zar", "18.20"))
        self.phone_prefix_input.setText(settings.get("phone_country_code", "+263"))

    def handle_test_print(self):
        printer_name = self.printer_combo.currentData()
        if not printer_name:
            QMessageBox.warning(self, "No Printer Selected", "Please select a receipt printer from the dropdown first.")
            return

        paper_width = self.paper_width_combo.currentData() or "80"
        self.test_status_label.setText("Sending test print...")
        self.test_status_label.setStyleSheet("color: #0284C7; font-size: 12px;")

        success, msg = test_print_thermal_receipt(printer_name, paper_width)
        if success:
            self.test_status_label.setText("✓ Test receipt sent to printer!")
            self.test_status_label.setStyleSheet("color: #16A34A; font-size: 12px; font-weight: 700;")
            QMessageBox.information(
                self, "Test Print Sent",
                f"A sample supermarket-style receipt was sent to '{printer_name}'.\nCheck your receipt machine!"
            )
        else:
            self.test_status_label.setText("✗ Print failed")
            self.test_status_label.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 700;")
            QMessageBox.critical(
                self, "Test Print Failed",
                f"Could not print to '{printer_name}':\n{msg}\n\n"
                "Please verify the printer is turned on, connected, and has paper loaded."
            )

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
            "thermal_printer_name": self.printer_combo.currentData() or "",
            "thermal_paper_width": self.paper_width_combo.currentData() or "80",
            "thermal_auto_print": "1" if self.auto_print_check.isChecked() else "0",
            "thermal_cut_paper": "1" if self.cut_paper_check.isChecked() else "0",
            "rate_zig": self.rate_zig_input.text().strip() or "26.50",
            "rate_zar": self.rate_zar_input.text().strip() or "18.20",
            "phone_country_code": self.phone_prefix_input.text().strip() or "+263",
        }
        if not values["shop_name"]:
            QMessageBox.warning(self, "Validation Error", "Shop name is required.")
            return

        if update_settings(values):
            QMessageBox.information(self, "Saved", "Shop and printer settings updated successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")

