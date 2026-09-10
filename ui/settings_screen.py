import os
import shutil
import sqlite3
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QFileDialog, QMessageBox, QFrame, QFormLayout,
    QComboBox, QCheckBox, QScrollArea, QTabWidget, QGridLayout
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from managers.settings_manager import get_all_settings, update_settings
from utils.thermal_receipt import get_available_printers, test_print_thermal_receipt
from utils.whatsapp_helper import build_credit_reminder_message
from database.db_manager import get_connection, DB_PATH
from ui.theme import (
    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_PRIMARY_ORANGE,
    COLOR_CANVAS_BG, ScreenHeader, ICON_SETTINGS,
    set_btn_icon, ICON_FOLDER, ICON_X, ICON_PRINTER, ICON_SEARCH, ICON_SAVE, ICON_DOWNLOAD
)


class SettingsScreen(QWidget):
    """Admin-only screen for shop branding, hardware, multi-currency, and system configuration.
    
    Organized into clean, responsive category tabs with real-time interactive previews:
    - Store Profile & Identity (with live 80mm thermal receipt simulator)
    - Thermal Receipt Machine (ESC/POS hardware diagnostics, paper width, automation)
    - Multi-Currency & WhatsApp (live tender calculator and WhatsApp message preview)
    - System & Diagnostics (database health check, 1-click backup, and catalog metrics)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logo_path = ""
        self._is_dirty = False
        self._is_loading = False
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        self.setObjectName("settingsScreen")
        self.setStyleSheet(f"""
            QWidget#settingsScreen {{
                background-color: {COLOR_CANVAS_BG};
            }}
            QLabel {{
                border: none;
                background: transparent;
                padding: 0px;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QFrame#settingsCard {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 10px;
                padding: 16px;
            }}
            QFrame#ticketFrame {{
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 14px;
            }}
            QFrame#ticketFrame QLabel {{
                border: none;
                background: transparent;
                padding: 0px;
            }}
            QFrame#calcBox {{
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 12px;
            }}
            QFrame#calcBox QLabel {{
                border: none;
                background: transparent;
            }}
            QFrame#waBubble {{
                background-color: #DCF8C6;
                border: 1px solid #C4E1A4;
                border-radius: 8px;
                padding: 10px;
            }}
            QFrame#waBubble QLabel {{
                border: none;
                background: transparent;
            }}
            QFrame#statBox {{
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px 14px;
            }}
            QFrame#statBox QLabel {{
                border: none;
                background: transparent;
            }}
            QFrame#tipBox {{
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }}
            QFrame#tipBox QLabel {{
                border: none;
                background: transparent;
                padding: 0px;
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                min-height: 24px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid #F97316;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left-width: 0px;
            }}
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 16, 24, 16)
        root_layout.setSpacing(12)

        # 1. Header
        root_layout.addWidget(ScreenHeader(
            ICON_SETTINGS,
            "System Settings & Configuration",
            "Configure your store branding, thermal receipt hardware, daily exchange rates, and WhatsApp messaging.",
        ))

        # 2. Modern Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                background: #FFFFFF;
                border-radius: 8px;
                padding: 2px;
            }
            QTabBar::tab {
                background: #F1F5F9;
                color: #64748B;
                padding: 10px 22px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                min-width: 130px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #F97316;
                border-bottom: 3px solid #F97316;
                font-weight: 700;
            }
            QTabBar::tab:hover:!selected {
                background: #E2E8F0;
                color: #0F172A;
            }
        """)

        # Add Category Tabs (using && so ampersand is displayed literally in Qt)
        self.tabs.addTab(self._create_branding_tab(), "Store Profile")
        self.tabs.addTab(self._create_printer_tab(), "Thermal Printer (ESC/POS)")
        self.tabs.addTab(self._create_currency_tab(), "Currency && WhatsApp")
        self.tabs.addTab(self._create_system_tab(), "System Info")

        root_layout.addWidget(self.tabs, 1)

        # 3. Sticky Bottom Action Bar
        root_layout.addWidget(self._create_footer_bar())

    # =========================================================================
    # TAB 1: STORE PROFILE & LIVE RECEIPT PREVIEW
    # =========================================================================
    def _create_branding_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        # Left Column: Configuration Form
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        form_card = self._create_card_frame()
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setSpacing(12)

        card_title = QLabel("Store Identity & Receipt Details")
        card_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        form_card_layout.addWidget(card_title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft)

        self.shop_name_input = QLineEdit()
        self.shop_name_input.setPlaceholderText("e.g. Motor Spares Express")
        self.shop_name_input.textChanged.connect(self._on_branding_changed)
        form.addRow(self._make_field_label("Shop Name *"), self.shop_name_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("e.g. 123 Auto Lane, Bulawayo, Zimbabwe")
        self.address_input.textChanged.connect(self._on_branding_changed)
        form.addRow(self._make_field_label("Store Address"), self.address_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("e.g. +263 77 123 4567")
        self.phone_input.textChanged.connect(self._on_branding_changed)
        form.addRow(self._make_field_label("Store Phone"), self.phone_input)

        self.footer_input = QTextEdit()
        self.footer_input.setMaximumHeight(70)
        self.footer_input.setPlaceholderText("e.g. Goods once sold are non-refundable. Thank you for your business!")
        self.footer_input.textChanged.connect(self._on_branding_changed)
        form.addRow(self._make_field_label("Receipt Footer"), self.footer_input)

        form_card_layout.addLayout(form)
        left_col.addWidget(form_card)

        # Logo Card
        logo_card = self._create_card_frame()
        logo_layout = QVBoxLayout(logo_card)
        logo_layout.setSpacing(10)

        logo_title = QLabel("Receipt Logo Graphic")
        logo_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        logo_layout.addWidget(logo_title)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(14)

        self.logo_preview = QLabel("No Logo")
        self.logo_preview.setFixedSize(84, 84)
        self.logo_preview.setStyleSheet(f"""
            border: 2px dashed {COLOR_BORDER};
            background-color: #F8FAFC;
            border-radius: 8px;
            color: #94A3B8;
            font-size: 11px;
            font-weight: 600;
        """)
        self.logo_preview.setAlignment(Qt.AlignCenter)
        logo_row.addWidget(self.logo_preview)

        logo_btn_col = QVBoxLayout()
        logo_btn_col.setSpacing(8)

        choose_logo_btn = QPushButton("Choose Image...")
        choose_logo_btn.setFixedHeight(34)
        choose_logo_btn.setStyleSheet("""
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
        choose_logo_btn.clicked.connect(self.choose_logo)
        set_btn_icon(choose_logo_btn, ICON_FOLDER, size=14, color='#475569')
        logo_btn_col.addWidget(choose_logo_btn)

        clear_logo_btn = QPushButton("Remove Logo")
        clear_logo_btn.setFixedHeight(30)
        clear_logo_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FECACA;
                border-radius: 6px;
                font-weight: 600;
                padding: 0px 12px;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
                border-color: #F87171;
            }
        """)
        clear_logo_btn.clicked.connect(self.clear_logo)
        set_btn_icon(clear_logo_btn, ICON_X, size=13, color='#DC2626')
        logo_btn_col.addWidget(clear_logo_btn)

        logo_hint = QLabel("PNG or JPG (high-contrast monochrome logos print best on thermal paper)")
        logo_hint.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_SECONDARY};")
        logo_hint.setWordWrap(True)
        logo_btn_col.addWidget(logo_hint)

        logo_row.addLayout(logo_btn_col, 1)
        logo_layout.addLayout(logo_row)
        left_col.addWidget(logo_card)
        left_col.addStretch()

        layout.addLayout(left_col, 5)

        # Right Column: Live Simulated Thermal Receipt
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        preview_card = self._create_card_frame()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setSpacing(10)

        preview_header_row = QHBoxLayout()
        preview_title = QLabel("Live 80mm Receipt Simulator")
        preview_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        preview_header_row.addWidget(preview_title)

        live_badge = QLabel("LIVE PREVIEW")
        live_badge.setStyleSheet("""
            background-color: #DCFCE7;
            color: #15803D;
            font-size: 10px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 10px;
        """)
        preview_header_row.addWidget(live_badge)
        preview_header_row.addStretch()
        preview_layout.addLayout(preview_header_row)

        preview_sub = QLabel("Updates in real-time as you type your store branding:")
        preview_sub.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_SECONDARY};")
        preview_layout.addWidget(preview_sub)

        # The simulated paper ticket — fixed 380px wide (≈ 80mm thermal paper)
        # centred inside the preview panel via a wrapper row.
        ticket_wrapper = QHBoxLayout()
        ticket_wrapper.setContentsMargins(0, 0, 0, 0)

        self.ticket_frame = QFrame()
        self.ticket_frame.setObjectName("ticketFrame")
        self.ticket_frame.setFixedWidth(380)
        ticket_layout = QVBoxLayout(self.ticket_frame)
        ticket_layout.setSpacing(4)
        ticket_layout.setContentsMargins(16, 12, 16, 12)
        ticket_layout.setAlignment(Qt.AlignTop)

        # Logo / Name in ticket
        self.ticket_logo = QLabel()
        self.ticket_logo.setAlignment(Qt.AlignCenter)
        self.ticket_logo.setVisible(False)
        ticket_layout.addWidget(self.ticket_logo)

        self.ticket_shop_name = QLabel("MOTOR SPARES MANAGEMENT")
        self.ticket_shop_name.setAlignment(Qt.AlignCenter)
        self.ticket_shop_name.setStyleSheet("font-size: 14px; font-weight: 800; color: #0F172A;")
        ticket_layout.addWidget(self.ticket_shop_name)

        self.ticket_address = QLabel("123 Auto Lane, Bulawayo, Zimbabwe")
        self.ticket_address.setAlignment(Qt.AlignCenter)
        self.ticket_address.setStyleSheet("font-size: 11px; color: #475569;")
        self.ticket_address.setWordWrap(True)
        ticket_layout.addWidget(self.ticket_address)

        self.ticket_phone = QLabel("TEL: +263 77 123 4567")
        self.ticket_phone.setAlignment(Qt.AlignCenter)
        self.ticket_phone.setStyleSheet("font-size: 11px; color: #475569;")
        ticket_layout.addWidget(self.ticket_phone)

        sep1 = QLabel("----------------------------------------")
        sep1.setAlignment(Qt.AlignCenter)
        sep1.setStyleSheet("color: #94A3B8; font-family: monospace; font-size: 11px;")
        ticket_layout.addWidget(sep1)

        meta_label = QLabel("RCPT: #REC-001042       2026-09-09 14:30\nCASHIER: Admin          MODE: Cash (USD)")
        meta_label.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 10px; color: #334155;")
        ticket_layout.addWidget(meta_label)

        sep2 = QLabel("----------------------------------------")
        sep2.setAlignment(Qt.AlignCenter)
        sep2.setStyleSheet("color: #94A3B8; font-family: monospace; font-size: 11px;")
        ticket_layout.addWidget(sep2)

        items_label = QLabel(
            "1x  Oil Filter Toyota D4D         $12.50\n"
            "2x  NGK Spark Plug BKR6E          $10.00\n"
            "1x  Front Brake Pad Set           $24.00"
        )
        items_label.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 10px; color: #1E293B;")
        ticket_layout.addWidget(items_label)

        sep3 = QLabel("----------------------------------------")
        sep3.setAlignment(Qt.AlignCenter)
        sep3.setStyleSheet("color: #94A3B8; font-family: monospace; font-size: 11px;")
        ticket_layout.addWidget(sep3)

        totals_label = QLabel(
            "SUBTOTAL:                         $46.50\n"
            "DISCOUNT (0%):                     $0.00\n"
            "GRAND TOTAL (USD):                $46.50\n"
            "TENDERED (USD):                   $50.00\n"
            "CHANGE (USD):                      $3.50"
        )
        totals_label.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; font-weight: 700; color: #0F172A;")
        ticket_layout.addWidget(totals_label)

        sep4 = QLabel("----------------------------------------")
        sep4.setAlignment(Qt.AlignCenter)
        sep4.setStyleSheet("color: #94A3B8; font-family: monospace; font-size: 11px;")
        ticket_layout.addWidget(sep4)

        self.ticket_footer = QLabel("Thank you for your business!")
        self.ticket_footer.setAlignment(Qt.AlignCenter)
        self.ticket_footer.setStyleSheet("font-size: 11px; font-style: italic; color: #475569;")
        self.ticket_footer.setWordWrap(True)
        ticket_layout.addWidget(self.ticket_footer)

        barcode_sim = QLabel("||| | ||||| || |||||| |||| | |||| |||")
        barcode_sim.setAlignment(Qt.AlignCenter)
        barcode_sim.setStyleSheet("font-size: 16px; letter-spacing: 2px; color: #0F172A; margin-top: 6px;")
        ticket_layout.addWidget(barcode_sim)

        ticket_wrapper.addStretch()
        ticket_wrapper.addWidget(self.ticket_frame)
        ticket_wrapper.addStretch()

        preview_layout.addLayout(ticket_wrapper)
        preview_layout.addStretch()

        right_col.addWidget(preview_card)
        layout.addLayout(right_col, 4)

        scroll.setWidget(container)
        return scroll

    # =========================================================================
    # TAB 2: THERMAL RECEIPT PRINTER (ESC/POS) - 2-COLUMN BALANCED LAYOUT
    # =========================================================================
    def _create_printer_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        # Left Column: Hardware & Paper Roll Specs
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        hw_card = self._create_card_frame()
        hw_layout = QVBoxLayout(hw_card)
        hw_layout.setSpacing(14)

        hw_title = QLabel("Thermal Printer Hardware (ESC/POS)")
        hw_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        hw_layout.addWidget(hw_title)

        hw_subtitle = QLabel(
            "Connect your point-of-sale receipt machine (Epson TM-T88, Xprinter, POS-80, POS-58, Bixolon, etc.). "
            "Receipts print automatically on narrow rolls without standard print dialogs."
        )
        hw_subtitle.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY};")
        hw_subtitle.setWordWrap(True)
        hw_layout.addWidget(hw_subtitle)

        hw_form = QFormLayout()
        hw_form.setSpacing(12)

        # Printer selector row
        printer_row = QHBoxLayout()
        printer_row.setSpacing(8)

        self.printer_combo = QComboBox()
        self.printer_combo.currentIndexChanged.connect(self._on_printer_selected)
        printer_row.addWidget(self.printer_combo, 1)

        refresh_prt_btn = QPushButton("⟳ Scan")
        refresh_prt_btn.setFixedHeight(34)
        refresh_prt_btn.setStyleSheet("""
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
        refresh_prt_btn.setToolTip("Rescan Windows USB and network printers")
        refresh_prt_btn.clicked.connect(self.populate_printers)
        printer_row.addWidget(refresh_prt_btn)

        hw_form.addRow(self._make_field_label("Printer Device:"), printer_row)

        # Printer status pill
        self.printer_status_pill = QLabel("No printer selected")
        self.printer_status_pill.setStyleSheet("""
            background-color: #F1F5F9;
            color: #475569;
            font-size: 11px;
            font-weight: 600;
            padding: 5px 12px;
            border-radius: 4px;
        """)
        hw_form.addRow(self._make_field_label("Hardware Status:"), self.printer_status_pill)

        # Paper Roll Width
        self.paper_width_combo = QComboBox()
        self.paper_width_combo.addItem("80mm (Standard Supermarket Roll - 48 cols)", "80")
        self.paper_width_combo.addItem("58mm (Compact Mobile Roll - 32 cols)", "58")
        self.paper_width_combo.currentIndexChanged.connect(self._mark_dirty)
        hw_form.addRow(self._make_field_label("Roll Width:"), self.paper_width_combo)

        hw_layout.addLayout(hw_form)
        left_col.addWidget(hw_card)

        # Automation Options Card
        auto_card = self._create_card_frame()
        auto_layout = QVBoxLayout(auto_card)
        auto_layout.setSpacing(12)

        auto_title = QLabel("Checkout Automation")
        auto_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        auto_layout.addWidget(auto_title)

        auto_form = QFormLayout()
        auto_form.setSpacing(12)

        self.auto_print_check = QCheckBox("Automatically print receipt upon checkout in POS")
        self.auto_print_check.setChecked(True)
        self.auto_print_check.setStyleSheet("font-size: 13px; font-weight: 500; color: #1E293B;")
        self.auto_print_check.toggled.connect(self._mark_dirty)
        auto_form.addRow(self._make_field_label("Instant Print:"), self.auto_print_check)

        self.cut_paper_check = QCheckBox("Send ESC/POS automatic paper feed & guillotine cut code")
        self.cut_paper_check.setChecked(True)
        self.cut_paper_check.setStyleSheet("font-size: 13px; font-weight: 500; color: #1E293B;")
        self.cut_paper_check.toggled.connect(self._mark_dirty)
        auto_form.addRow(self._make_field_label("Auto-Cutter:"), self.cut_paper_check)

        auto_layout.addLayout(auto_form)
        left_col.addWidget(auto_card)
        left_col.addStretch()

        layout.addLayout(left_col, 5)

        # Right Column: Diagnostics & Hardware Test Bench
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        test_card = self._create_card_frame()
        test_layout = QVBoxLayout(test_card)
        test_layout.setSpacing(14)

        test_title = QLabel("Hardware Diagnostic & Test Bench")
        test_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        test_layout.addWidget(test_title)

        test_desc = QLabel(
            "Send an instant raw ESC/POS test receipt to confirm printer paper feed, "
            "thermal print head alignment, and automatic paper cutter:"
        )
        test_desc.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY};")
        test_desc.setWordWrap(True)
        test_layout.addWidget(test_desc)

        test_action_row = QHBoxLayout()
        test_action_row.setSpacing(14)

        self.test_print_btn = QPushButton("Send Test Print Receipt")
        self.test_print_btn.setFixedHeight(40)
        self.test_print_btn.setStyleSheet("""
            QPushButton {
                background-color: #0F172A;
                color: #FFFFFF;
                border: 1px solid #0F172A;
                border-radius: 6px;
                font-weight: 700;
                font-size: 13px;
                padding: 0px 22px;
            }
            QPushButton:hover {
                background-color: #1E293B;
                border-color: #334155;
            }
        """)
        self.test_print_btn.clicked.connect(self.handle_test_print)
        set_btn_icon(self.test_print_btn, ICON_PRINTER, size=14, color='#FFFFFF')
        test_action_row.addWidget(self.test_print_btn)

        self.test_status_label = QLabel("Ready to test")
        self.test_status_label.setStyleSheet("font-size: 12px; color: #64748B;")
        test_action_row.addWidget(self.test_status_label, 1)

        test_layout.addLayout(test_action_row)

        # Connection hints box
        hint_box = self._make_tip_box("Setup Tips & Troubleshooting:", [
            "• USB Connection: Ensure Windows displays your printer under 'Printers & Scanners'.",
            "• Paper Roll: Thermal paper must face the thermal print head (coated heat-sensitive side).",
            "• Network/LAN: Configure as Windows shared printer or standard TCP/IP port.",
            "• Driverless ESC/POS: Motor Spares sends standard raw byte commands directly."
        ])
        test_layout.addWidget(hint_box)

        right_col.addWidget(test_card)
        right_col.addStretch()
        layout.addLayout(right_col, 5)

        scroll.setWidget(container)
        return scroll

    # =========================================================================
    # TAB 3: MULTI-CURRENCY & WHATSAPP
    # =========================================================================
    def _create_currency_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        # Left Column: Currency Exchange Engine
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        curr_card = self._create_card_frame()
        curr_layout = QVBoxLayout(curr_card)
        curr_layout.setSpacing(12)

        curr_title = QLabel("Multi-Currency Counter Engine (Southern Africa)")
        curr_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        curr_layout.addWidget(curr_title)

        curr_sub = QLabel(
            "Set daily counter exchange rates against Base USD. "
            "The POS checkout dynamically accepts mixed tenders (USD cash, EcoCash ZiG, Swipe, or ZAR Rand)."
        )
        curr_sub.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY};")
        curr_sub.setWordWrap(True)
        curr_layout.addWidget(curr_sub)

        curr_form = QFormLayout()
        curr_form.setSpacing(12)

        self.rate_zig_input = QLineEdit()
        self.rate_zig_input.setPlaceholderText("e.g. 26.50")
        self.rate_zig_input.textChanged.connect(self._on_currency_changed)
        curr_form.addRow(self._make_field_label("USD to ZiG Rate (1 USD = X ZiG):"), self.rate_zig_input)

        self.rate_zar_input = QLineEdit()
        self.rate_zar_input.setPlaceholderText("e.g. 18.20")
        self.rate_zar_input.textChanged.connect(self._on_currency_changed)
        curr_form.addRow(self._make_field_label("USD to ZAR Rate (1 USD = X ZAR):"), self.rate_zar_input)

        curr_layout.addLayout(curr_form)

        # Quick Rate Presets
        preset_box = QHBoxLayout()
        preset_box.setSpacing(8)
        preset_lbl = QLabel("Quick Presets:")
        preset_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        preset_box.addWidget(preset_lbl)

        btn_zig_26 = QPushButton("ZiG 26.50")
        btn_zig_26.setFixedHeight(24)
        btn_zig_26.setStyleSheet("font-size: 11px; padding: 2px 8px; border: 1px solid #CBD5E1; border-radius: 4px; background: #F8FAFC;")
        btn_zig_26.clicked.connect(lambda: self.rate_zig_input.setText("26.50"))
        preset_box.addWidget(btn_zig_26)

        btn_zig_27 = QPushButton("ZiG 27.00")
        btn_zig_27.setFixedHeight(24)
        btn_zig_27.setStyleSheet("font-size: 11px; padding: 2px 8px; border: 1px solid #CBD5E1; border-radius: 4px; background: #F8FAFC;")
        btn_zig_27.clicked.connect(lambda: self.rate_zig_input.setText("27.00"))
        preset_box.addWidget(btn_zig_27)

        btn_zar_18 = QPushButton("ZAR 18.20")
        btn_zar_18.setFixedHeight(24)
        btn_zar_18.setStyleSheet("font-size: 11px; padding: 2px 8px; border: 1px solid #CBD5E1; border-radius: 4px; background: #F8FAFC;")
        btn_zar_18.clicked.connect(lambda: self.rate_zar_input.setText("18.20"))
        preset_box.addWidget(btn_zar_18)

        preset_box.addStretch()
        curr_layout.addLayout(preset_box)

        # Interactive Rate Calculator Box
        calc_box = QFrame()
        calc_box.setObjectName("calcBox")
        calc_layout = QVBoxLayout(calc_box)
        calc_layout.setSpacing(8)

        calc_title = QLabel("Live Counter Rate Calculator Test")
        calc_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #0F172A;")
        calc_layout.addWidget(calc_title)

        calc_row = QHBoxLayout()
        lbl_usd = QLabel("Test Tender: $")
        lbl_usd.setStyleSheet("font-weight: 600; color: #334155;")
        calc_row.addWidget(lbl_usd)

        self.calc_usd_input = QLineEdit("10.00")
        self.calc_usd_input.setFixedWidth(80)
        self.calc_usd_input.textChanged.connect(self._update_calculator)
        calc_row.addWidget(self.calc_usd_input)

        lbl_usd_suffix = QLabel("USD")
        lbl_usd_suffix.setStyleSheet("font-weight: 600; color: #64748B;")
        calc_row.addWidget(lbl_usd_suffix)
        calc_row.addStretch()
        calc_layout.addLayout(calc_row)

        self.calc_result_label = QLabel("= 265.00 ZiG   |   = 182.00 ZAR")
        self.calc_result_label.setStyleSheet("font-size: 13px; font-weight: 800; color: #D97706; padding: 2px 0;")
        calc_layout.addWidget(self.calc_result_label)

        curr_layout.addWidget(calc_box)
        left_col.addWidget(curr_card)
        left_col.addStretch()
        layout.addLayout(left_col, 5)

        # Right Column: WhatsApp Direct Integration
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        wa_card = self._create_card_frame()
        wa_layout = QVBoxLayout(wa_card)
        wa_layout.setSpacing(12)

        wa_title = QLabel("WhatsApp Direct Messaging")
        wa_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        wa_layout.addWidget(wa_title)

        wa_sub = QLabel(
            "Send 1-click overdue credit reminders and digital receipt slips directly to customers' WhatsApp "
            "without manual typing."
        )
        wa_sub.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY};")
        wa_sub.setWordWrap(True)
        wa_layout.addWidget(wa_sub)

        wa_form = QFormLayout()
        wa_form.setSpacing(12)

        self.phone_prefix_input = QLineEdit()
        self.phone_prefix_input.setPlaceholderText("+263")
        self.phone_prefix_input.textChanged.connect(self._on_whatsapp_changed)
        wa_form.addRow(self._make_field_label("Default Country Prefix:"), self.phone_prefix_input)

        wa_layout.addLayout(wa_form)

        prefix_hint = QLabel("Common: +263 (Zimbabwe), +27 (South Africa), +267 (Botswana), +260 (Zambia)")
        prefix_hint.setStyleSheet("font-size: 11px; color: #64748B;")
        wa_layout.addWidget(prefix_hint)

        # Simulated WhatsApp Chat Window
        chat_box = QFrame()
        chat_box.setStyleSheet("""
            QFrame {
                background-color: #EFEAE2;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        chat_layout = QVBoxLayout(chat_box)
        chat_layout.setSpacing(8)

        # Chat Top Bar
        chat_top = QHBoxLayout()
        wa_icon = QLabel("[WA]")
        chat_top.addWidget(wa_icon)
        chat_contact = QLabel("John Doe (Customer)")
        chat_contact.setStyleSheet("font-size: 12px; font-weight: 700; color: #075E54;")
        chat_top.addWidget(chat_contact)
        chat_top.addStretch()
        chat_layout.addLayout(chat_top)

        # Message Bubble
        bubble = QFrame()
        bubble.setObjectName("waBubble")
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setSpacing(4)

        self.wa_bubble_text = QLabel(
            "Hello John Doe,\n\n"
            "This is a courtesy reminder from *Motor Spares Management*.\n"
            "You have an outstanding balance of *$145.00* for Credit Order *#1042* due on 15 Sept.\n\n"
            "Kindly arrange settlement at your earliest convenience."
        )
        self.wa_bubble_text.setStyleSheet("font-size: 12px; color: #0F172A;")
        self.wa_bubble_text.setWordWrap(True)
        bubble_layout.addWidget(self.wa_bubble_text)

        wa_time = QLabel("10:42 AM  ✓✓")
        wa_time.setAlignment(Qt.AlignRight)
        wa_time.setStyleSheet("font-size: 10px; color: #4B5563;")
        bubble_layout.addWidget(wa_time)

        chat_layout.addWidget(bubble)
        wa_layout.addWidget(chat_box)

        right_col.addWidget(wa_card)
        right_col.addStretch()
        layout.addLayout(right_col, 5)

        scroll.setWidget(container)
        return scroll

    # =========================================================================
    # TAB 4: SYSTEM INFO & DIAGNOSTICS - 2-COLUMN BALANCED LAYOUT
    # =========================================================================
    def _create_system_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        # Left Column: Software Architecture & Inventory Metrics
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        info_card = self._create_card_frame()
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(14)

        info_title = QLabel("Software & Database Engine")
        info_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        info_layout.addWidget(info_title)

        grid = QGridLayout()
        grid.setSpacing(10)

        def make_stat_box(title: str, val: str, icon: str = ""):
            frame = QFrame()
            frame.setObjectName("statBox")
            fl = QVBoxLayout(frame)
            fl.setSpacing(4)
            prefix = f"{icon} " if icon else ""
            lbl_title = QLabel(f"{prefix}{title}")
            lbl_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
            lbl_val = QLabel(val)
            lbl_val.setStyleSheet("font-size: 13px; font-weight: 700; color: #0F172A;")
            fl.addWidget(lbl_title)
            fl.addWidget(lbl_val)
            return frame

        # Compute database file size
        db_size_str = "Unknown"
        if os.path.exists(DB_PATH):
            sz = os.path.getsize(DB_PATH)
            if sz < 1024 * 1024:
                db_size_str = f"{sz / 1024:.1f} KB"
            else:
                db_size_str = f"{sz / (1024 * 1024):.2f} MB"

        grid.addWidget(make_stat_box("Application Version", "v2.4.0 Commercial", ""), 0, 0)
        grid.addWidget(make_stat_box("Database Engine", "SQLite 3 (WAL)", ""), 0, 1)
        grid.addWidget(make_stat_box("Database Storage", f"{db_size_str}", ""), 1, 0)
        grid.addWidget(make_stat_box("Connection Status", "Online & Operational", ""), 1, 1)

        info_layout.addLayout(grid)
        left_col.addWidget(info_card)

        # Catalog Metrics Card
        metrics_card = self._create_card_frame()
        metrics_layout = QVBoxLayout(metrics_card)
        metrics_layout.setSpacing(12)

        m_title = QLabel("Catalog & Business Volume")
        m_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        metrics_layout.addWidget(m_title)

        m_grid = QGridLayout()
        m_grid.setSpacing(10)

        # Query live counts
        parts_cnt = "0"
        cust_cnt = "0"
        users_cnt = "0"
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Part;")
            parts_cnt = f"{cursor.fetchone()[0]:,}"
            cursor.execute("SELECT COUNT(*) FROM Customer;")
            cust_cnt = f"{cursor.fetchone()[0]:,}"
            cursor.execute("SELECT COUNT(*) FROM User;")
            users_cnt = f"{cursor.fetchone()[0]:,}"
            conn.close()
        except Exception:
            pass

        m_grid.addWidget(make_stat_box("Active Catalog Parts", parts_cnt, ""), 0, 0)
        m_grid.addWidget(make_stat_box("Registered Customers", cust_cnt, ""), 0, 1)
        m_grid.addWidget(make_stat_box("System Operators", users_cnt, ""), 1, 0)
        m_grid.addWidget(make_stat_box("Architecture", "64-Bit Local Embedded", ""), 1, 1)

        metrics_layout.addLayout(m_grid)
        left_col.addWidget(metrics_card)
        left_col.addStretch()

        layout.addLayout(left_col, 5)

        # Right Column: Database Maintenance & Safety
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        maint_card = self._create_card_frame()
        maint_layout = QVBoxLayout(maint_card)
        maint_layout.setSpacing(14)

        maint_title = QLabel("Database Integrity & Safety")
        maint_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        maint_layout.addWidget(maint_title)

        maint_desc = QLabel(
            "Perform live database health diagnostics and trigger immediate local snapshot backups "
            "to safeguard your sales transactions and stock records:"
        )
        maint_desc.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY};")
        maint_desc.setWordWrap(True)
        maint_layout.addWidget(maint_desc)

        # Health check action
        diag_row = QHBoxLayout()
        diag_row.setSpacing(12)
        diag_btn = QPushButton("Run Health Check")
        diag_btn.setFixedHeight(36)
        diag_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-weight: 600;
                padding: 0px 16px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                border-color: #94A3B8;
            }
        """)
        diag_btn.clicked.connect(self._run_db_integrity_check)
        set_btn_icon(diag_btn, ICON_SEARCH, size=14, color='#475569')
        diag_row.addWidget(diag_btn)

        self.db_status_label = QLabel("Click to verify tables")
        self.db_status_label.setStyleSheet("font-size: 12px; color: #64748B;")
        diag_row.addWidget(self.db_status_label, 1)
        maint_layout.addLayout(diag_row)

        # 1-Click Backup Action
        backup_row = QHBoxLayout()
        backup_row.setSpacing(12)
        backup_btn = QPushButton("1-Click DB Backup")
        backup_btn.setFixedHeight(36)
        backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #ECFDF5;
                color: #047857;
                border: 1px solid #A7F3D0;
                border-radius: 6px;
                font-weight: 700;
                padding: 0px 16px;
            }
            QPushButton:hover {
                background-color: #D1FAE5;
                border-color: #6EE7B7;
            }
        """)
        backup_btn.clicked.connect(self._create_instant_backup)
        set_btn_icon(backup_btn, ICON_DOWNLOAD, size=14, color='#047857')
        backup_row.addWidget(backup_btn)

        self.backup_status_label = QLabel("Saved to /backups folder")
        self.backup_status_label.setStyleSheet("font-size: 12px; color: #64748B;")
        backup_row.addWidget(self.backup_status_label, 1)
        maint_layout.addLayout(backup_row)

        # Security notes box
        sec_box = self._make_tip_box("Data Protection & Security:", [
            "• Local Sovereignty: Your database resides entirely on your premise without cloud lock-in.",
            "• WAL Mode: SQLite Write-Ahead Logging protects against power-cut corruption.",
            "• Automated Backups: You can copy the /backups folder to an external USB flash drive anytime."
        ])
        maint_layout.addWidget(sec_box)

        right_col.addWidget(maint_card)
        right_col.addStretch()

        layout.addLayout(right_col, 5)

        scroll.setWidget(container)
        return scroll

    # =========================================================================
    # FOOTER BAR
    # =========================================================================
    def _create_footer_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 6px 14px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        bar_layout.setSpacing(14)

        # Status badge
        self.dirty_status_label = QLabel("✓ All settings up to date")
        self.dirty_status_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #16A34A;")
        bar_layout.addWidget(self.dirty_status_label)

        bar_layout.addStretch()

        # Discard button
        self.discard_btn = QPushButton("↺ Discard Changes")
        self.discard_btn.setFixedHeight(36)
        self.discard_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-weight: 600;
                padding: 0px 16px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                color: #0F172A;
            }
        """)
        self.discard_btn.clicked.connect(self.load_settings)
        bar_layout.addWidget(self.discard_btn)

        # Save button
        self.save_btn = QPushButton("Save All Settings")
        self.save_btn.setFixedHeight(36)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_ORANGE};
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                padding: 0px 24px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
            QPushButton:pressed {{
                background-color: #C2410C;
            }}
        """)
        self.save_btn.clicked.connect(self.save_settings)
        set_btn_icon(self.save_btn, ICON_SAVE, size=14, color='#FFFFFF')
        bar_layout.addWidget(self.save_btn)

        return bar

    # =========================================================================
    # HELPERS & UI STYLING
    # =========================================================================
    def _create_card_frame(self) -> QFrame:
        card = QFrame()
        card.setObjectName("settingsCard")
        return card

    def _make_field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
        return lbl

    def _make_tip_box(self, title: str, bullets: list) -> QFrame:
        box = QFrame()
        box.setObjectName("tipBox")
        bl = QVBoxLayout(box)
        bl.setSpacing(6)
        bl.setContentsMargins(12, 12, 12, 12)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #1E293B;")
        bl.addWidget(t_lbl)

        for b in bullets:
            b_lbl = QLabel(b)
            b_lbl.setWordWrap(True)
            b_lbl.setStyleSheet("font-size: 11px; color: #475569;")
            bl.addWidget(b_lbl)

        return box

    def _mark_dirty(self):
        if not self._is_loading:
            self._is_dirty = True
            self.dirty_status_label.setText("● Unsaved changes")
            self.dirty_status_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #D97706;")

    def _on_branding_changed(self):
        self._mark_dirty()
        self._update_ticket_preview()

    def _on_currency_changed(self):
        self._mark_dirty()
        self._update_calculator()

    def _on_whatsapp_changed(self):
        self._mark_dirty()
        self._update_whatsapp_preview()

    def _on_printer_selected(self):
        self._mark_dirty()
        printer_name = self.printer_combo.currentData()
        if printer_name:
            self.printer_status_pill.setText(f"Configured: {printer_name}")
            self.printer_status_pill.setStyleSheet("""
                background-color: #DCFCE7;
                color: #15803D;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 10px;
                border-radius: 4px;
            """)
        else:
            self.printer_status_pill.setText("No printer selected (defaulting to standard printing)")
            self.printer_status_pill.setStyleSheet("""
                background-color: #F1F5F9;
                color: #64748B;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 4px;
            """)

    def _update_ticket_preview(self):
        shop = self.shop_name_input.text().strip() or "MOTOR SPARES MANAGEMENT"
        self.ticket_shop_name.setText(shop.upper())

        addr = self.address_input.text().strip() or "123 Auto Lane, Bulawayo, Zimbabwe"
        self.ticket_address.setText(addr)

        phone = self.phone_input.text().strip() or "+263 77 123 4567"
        self.ticket_phone.setText(f"TEL: {phone}")

        footer = self.footer_input.toPlainText().strip() or "Thank you for your business!"
        self.ticket_footer.setText(footer)

        self._update_whatsapp_preview()

    def _update_calculator(self):
        try:
            usd_val = float(self.calc_usd_input.text().strip() or "0")
            zig_rate = float(self.rate_zig_input.text().strip() or "26.50")
            zar_rate = float(self.rate_zar_input.text().strip() or "18.20")

            zig_val = usd_val * zig_rate
            zar_val = usd_val * zar_rate
            self.calc_result_label.setText(f"= {zig_val:,.2f} ZiG   |   = {zar_val:,.2f} ZAR")
        except ValueError:
            self.calc_result_label.setText("Invalid rate or test number")

    def _update_whatsapp_preview(self):
        shop = self.shop_name_input.text().strip() or "Motor Spares Management"
        msg = build_credit_reminder_message(
            customer_name="John Doe",
            credit_order_id=1042,
            total_amount=145.00,
            due_date="15 Sept"
        )
        self.wa_bubble_text.setText(msg)

    # =========================================================================
    # DATA LOGIC & ACTIONS
    # =========================================================================
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
        self._is_loading = True
        self.populate_printers()
        settings = get_all_settings()

        # Branding
        self.shop_name_input.setText(settings.get("shop_name", ""))
        self.address_input.setText(settings.get("address", ""))
        self.phone_input.setText(settings.get("phone", ""))
        self.footer_input.setPlainText(settings.get("receipt_footer", ""))
        self.logo_path = settings.get("logo_path", "")
        self._refresh_logo_preview()

        # Thermal Printer
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

        # Currency & WhatsApp
        self.rate_zig_input.setText(settings.get("rate_zig", "26.50"))
        self.rate_zar_input.setText(settings.get("rate_zar", "18.20"))
        self.phone_prefix_input.setText(settings.get("phone_country_code", "+263"))

        self._on_printer_selected()
        self._update_ticket_preview()
        self._update_calculator()

        self._is_loading = False
        self._is_dirty = False
        self.dirty_status_label.setText("✓ All settings up to date")
        self.dirty_status_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #16A34A;")

    def _refresh_logo_preview(self):
        if self.logo_path and os.path.exists(self.logo_path):
            pixmap = QPixmap(self.logo_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_preview.setPixmap(scaled)
                self.logo_preview.setText("")

                # Also update ticket preview logo
                ticket_pix = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.ticket_logo.setPixmap(ticket_pix)
                self.ticket_logo.setVisible(True)
                return

        self.logo_preview.setPixmap(QPixmap())
        self.logo_preview.setText("No Logo")
        self.ticket_logo.setVisible(False)

    def choose_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Logo Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if path:
            self.logo_path = path
            self._refresh_logo_preview()
            self._mark_dirty()

    def clear_logo(self):
        self.logo_path = ""
        self._refresh_logo_preview()
        self._mark_dirty()

    def handle_test_print(self):
        printer_name = self.printer_combo.currentData()
        if not printer_name:
            QMessageBox.warning(self, "No Printer Selected", "Please select a thermal receipt printer from the dropdown first.")
            return

        paper_width = self.paper_width_combo.currentData() or "80"
        self.test_status_label.setText("Sending test print to hardware...")
        self.test_status_label.setStyleSheet("color: #0284C7; font-size: 12px; font-weight: 600;")

        success, msg = test_print_thermal_receipt(printer_name, paper_width)
        if success:
            self.test_status_label.setText("✓ Test receipt sent successfully!")
            self.test_status_label.setStyleSheet("color: #16A34A; font-size: 12px; font-weight: 700;")
            QMessageBox.information(
                self, "Hardware Test Sent",
                f"A sample supermarket-style receipt was sent to '{printer_name}'.\nCheck your receipt machine!"
            )
        else:
            self.test_status_label.setText("✗ Print failed - check connection")
            self.test_status_label.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 700;")
            QMessageBox.critical(
                self, "Hardware Test Failed",
                f"Could not print to '{printer_name}':\n{msg}\n\n"
                "Please verify the printer is turned on, USB cable connected, and paper roll loaded."
            )

    def _run_db_integrity_check(self):
        self.db_status_label.setText("Running integrity check...")
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            res = cursor.fetchone()
            conn.close()
            status = res[0] if res else "unknown"
            if status == "ok":
                self.db_status_label.setText("✓ Database integrity is 100% OK! No corruption.")
                self.db_status_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #16A34A;")
            else:
                self.db_status_label.setText(f"⚠️ Warning: {status}")
                self.db_status_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #DC2626;")
        except Exception as e:
            self.db_status_label.setText(f"Error checking database: {e}")
            self.db_status_label.setStyleSheet("font-size: 12px; color: #DC2626;")

    def _create_instant_backup(self):
        try:
            os.makedirs("backups", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join("backups", f"pos_backup_{timestamp}.db")
            shutil.copyfile(DB_PATH, dest)
            sz = os.path.getsize(dest)
            kb = sz / 1024
            self.backup_status_label.setText(f"✓ Backup saved! ({kb:.1f} KB)")
            self.backup_status_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #047857;")
            QMessageBox.information(
                self, "Backup Created",
                f"A snapshot of your database has been successfully saved to:\n\n{dest}\n\n"
                "You can keep this file or copy it to an external drive for disaster recovery."
            )
        except Exception as e:
            self.backup_status_label.setText(f"Backup failed: {e}")
            self.backup_status_label.setStyleSheet("font-size: 12px; color: #DC2626;")

    def save_settings(self):
        shop_name = self.shop_name_input.text().strip()
        if not shop_name:
            QMessageBox.warning(self, "Validation Error", "Shop name is required. Please enter a shop name.")
            self.tabs.setCurrentIndex(0)
            self.shop_name_input.setFocus()
            return

        values = {
            "shop_name": shop_name,
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

        if update_settings(values):
            self._is_dirty = False
            self.dirty_status_label.setText("✓ All settings saved successfully!")
            self.dirty_status_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #16A34A;")
            QMessageBox.information(self, "Settings Saved", "All store, hardware, and currency settings updated successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings to the database.")
