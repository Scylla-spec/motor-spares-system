"""
Theme and Design System for Motor Spares System.
Provides modern ERP aesthetics matching the reference design:
- Deep Navy Sidebar (#0F172A) with warm orange pill active state (#F97316)
- Crisp light canvas (#F8FAFC) with elevated white cards and subtle borders (#E2E8F0)
- Modern typography, stat metric cards, filter dropdowns, and pill status badges
"""

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QStyledItemDelegate
)
from PySide6.QtCore import Qt, QRect, QRectF, Signal, QByteArray, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer

# --- Color Palette Tokens ---
COLOR_SIDEBAR_BG = "#0F172A"       # Deep slate navy
COLOR_SIDEBAR_HOVER = "#1E293B"    # Subtle lighter navy
COLOR_SIDEBAR_TEXT = "#94A3B8"     # Muted grey text
COLOR_SIDEBAR_ACTIVE_BG = "#F97316" # Vibrant warm orange pill
COLOR_SIDEBAR_ACTIVE_TEXT = "#FFFFFF"

COLOR_CANVAS_BG = "#F8FAFC"        # Light neutral canvas
COLOR_CARD_BG = "#FFFFFF"          # Pure white card/table
COLOR_BORDER = "#E2E8F0"           # Light border
COLOR_BORDER_FOCUS = "#F97316"     # Focus highlight

COLOR_TEXT_PRIMARY = "#0F172A"     # Dark text
COLOR_TEXT_SECONDARY = "#64748B"   # Slate subtitle/label
COLOR_TEXT_MUTED = "#94A3B8"       # Disabled/placeholder

COLOR_PRIMARY_RED = "#991B1B"      # Dark crimson (Stock In / Action)
COLOR_PRIMARY_RED_HOVER = "#7F1D1D"
COLOR_PRIMARY_ORANGE = "#F97316"   # Orange accent button
COLOR_PRIMARY_ORANGE_HOVER = "#EA580C"
COLOR_SUCCESS = "#10B981"          # Emerald green
COLOR_WARNING = "#F59E0B"          # Amber
COLOR_DANGER = "#EF4444"           # Red

# Badge colors
COLOR_BADGE_NORMAL_BG = "#E0F2FE"
COLOR_BADGE_NORMAL_FG = "#0369A1"
COLOR_BADGE_LOW_BG = "#FFE4E6"
COLOR_BADGE_LOW_FG = "#BE123C"
COLOR_BADGE_ZERO_BG = "#991B1B"
COLOR_BADGE_ZERO_FG = "#FFFFFF"

# Global Application Stylesheet
GLOBAL_APP_QSS = f"""
QMainWindow, QDialog {{
    background-color: {COLOR_CANVAS_BG};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}}

QWidget {{
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}}

/* Line Edit / Inputs */
QLineEdit {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    selection-background-color: {COLOR_PRIMARY_ORANGE};
    min-height: 22px;
}}

QLineEdit:focus {{
    border: 1px solid {COLOR_PRIMARY_ORANGE};
    background-color: #FFFFFF;
}}

QLineEdit:disabled {{
    background-color: #F1F5F9;
    color: {COLOR_TEXT_MUTED};
    border: 1px solid #E2E8F0;
}}

/* SpinBox & DateEdit with explicit, high-contrast Up (▲) / Down (▼) arrow buttons */
QSpinBox, QDoubleSpinBox, QDateEdit {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 4px 28px 4px 8px;
    min-height: 26px;
    font-size: 13px;
}}

QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 1px solid {COLOR_PRIMARY_ORANGE};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button, QDateEdit::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    height: 14px;
    border-left: 1px solid #CBD5E1;
    border-bottom: 1px solid #E2E8F0;
    border-top-right-radius: 5px;
    background-color: #F8FAFC;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QDateEdit::up-button:hover {{
    background-color: #FFF7ED;
    border-color: #F97316;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QDateEdit::up-arrow {{
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><polygon points='5,0 10,6 0,6' fill='%230F172A'/></svg>");
    width: 10px;
    height: 6px;
}}

QSpinBox::up-button:hover QSpinBox::up-arrow, QDoubleSpinBox::up-button:hover QDoubleSpinBox::up-arrow, QDateEdit::up-button:hover QDateEdit::up-arrow {{
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><polygon points='5,0 10,6 0,6' fill='%23F97316'/></svg>");
}}

QSpinBox::down-button, QDoubleSpinBox::down-button, QDateEdit::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 24px;
    height: 14px;
    border-left: 1px solid #CBD5E1;
    border-bottom-right-radius: 5px;
    background-color: #F8FAFC;
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover, QDateEdit::down-button:hover {{
    background-color: #FFF7ED;
    border-color: #F97316;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QDateEdit::down-arrow {{
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><polygon points='0,0 10,0 5,6' fill='%230F172A'/></svg>");
    width: 10px;
    height: 6px;
}}

QSpinBox::down-button:hover QSpinBox::down-arrow, QDoubleSpinBox::down-button:hover QSpinBox::down-arrow, QDateEdit::down-button:hover QDateEdit::down-arrow {{
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><polygon points='0,0 10,0 5,6' fill='%23F97316'/></svg>");
}}

/* Combo Box */
QComboBox {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 5px 12px;
    min-height: 22px;
}}

QComboBox:hover {{
    border: 1px solid #CBD5E1;
    background-color: #F8FAFC;
}}

QComboBox:focus {{
    border: 1px solid {COLOR_PRIMARY_ORANGE};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left-width: 0px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    selection-background-color: #FFF7ED;
    selection-color: {COLOR_PRIMARY_ORANGE};
    padding: 4px;
    outline: none;
}}

/* Push Buttons */
QPushButton {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: #F1F5F9;
    border-color: #CBD5E1;
}}

QPushButton:pressed {{
    background-color: #E2E8F0;
}}

QPushButton:disabled {{
    background-color: #F1F5F9;
    color: {COLOR_TEXT_MUTED};
    border-color: #E2E8F0;
}}

/* Table Widget */
QTableWidget, QTableView {{
    background-color: #FFFFFF;
    gridline-color: #F1F5F9;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    selection-background-color: #F8FAFC;
    selection-color: {COLOR_TEXT_PRIMARY};
    outline: none;
}}

QHeaderView::section {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_SECONDARY};
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid #F1F5F9;
    border-right: 1px solid #F8FAFC;
}}

QTableWidget::item {{
    padding: 8px;
    border-bottom: 1px solid #F1F5F9;
}}

QTableWidget::item:selected {{
    background-color: #F8FAFC;
    color: {COLOR_TEXT_PRIMARY};
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid #E2E8F0;
    background: #FFFFFF;
    border-radius: 8px;
    padding: 8px;
    margin-top: 0px;
}}

QTabBar::tab {{
    background: #F1F5F9;
    color: #64748B;
    padding: 6px 14px;
    margin-right: 3px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
    font-size: 12px;
}}

QTabBar::tab:selected {{
    background: #FFFFFF;
    color: #F97316;
    border-bottom: 2px solid #F97316;
    font-weight: 700;
}}

/* ScrollBars */
QScrollBar:vertical {{
    background: #F1F5F9;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: #CBD5E1;
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #94A3B8;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: #F1F5F9;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: #CBD5E1;
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #94A3B8;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


# ---------------------------------------------------------------------------
# SVG Icon Path Data  (Feather Icons — MIT License, viewBox 0 0 24 24)
# ---------------------------------------------------------------------------
ICON_DASHBOARD = (
    '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
    '<polyline points="9 22 9 12 15 12 15 22"/>'
)
ICON_INVENTORY = (
    '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8'
    'a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
    '<polyline points="3.27 6.96 12 12.01 20.73 6.96"/>'
    '<line x1="12" y1="22.08" x2="12" y2="12"/>'
)
ICON_POS = (
    '<circle cx="9" cy="21" r="1"/>'
    '<circle cx="20" cy="21" r="1"/>'
    '<path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>'
)
ICON_CREDIT = (
    '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>'
    '<line x1="1" y1="10" x2="23" y2="10"/>'
)
ICON_CUSTOMERS = (
    '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
    '<circle cx="9" cy="7" r="4"/>'
    '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
    '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
)
ICON_SUPPLIERS = (
    '<rect x="1" y="3" width="15" height="13"/>'
    '<polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>'
    '<circle cx="5.5" cy="18.5" r="2.5"/>'
    '<circle cx="18.5" cy="18.5" r="2.5"/>'
)
ICON_REPORTS = (
    '<line x1="18" y1="20" x2="18" y2="10"/>'
    '<line x1="12" y1="20" x2="12" y2="4"/>'
    '<line x1="6" y1="20" x2="6" y2="14"/>'
)
ICON_USER_MGMT = (
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
    '<circle cx="12" cy="7" r="4"/>'
)
ICON_SETTINGS = (
    '<circle cx="12" cy="12" r="3"/>'
    '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83'
    'l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0'
    'v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83'
    '-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4'
    'h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83'
    '-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0'
    'v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83'
    ' 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4'
    'h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
)
ICON_LOGOUT = (
    '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
    '<polyline points="16 17 21 12 16 7"/>'
    '<line x1="21" y1="12" x2="9" y2="12"/>'
)

# --- Action / Button Icons (Feather Icons, MIT) ---
ICON_TRASH = (
    '<polyline points="3 6 5 6 21 6"/>'
    '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
    '<path d="M10 11v6"/>'
    '<path d="M14 11v6"/>'
    '<path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>'
)
ICON_PDF = (
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    '<polyline points="14 2 14 8 20 8"/>'
    '<line x1="16" y1="13" x2="8" y2="13"/>'
    '<line x1="16" y1="17" x2="8" y2="17"/>'
    '<polyline points="10 9 9 9 8 9"/>'
)
ICON_DOWNLOAD = (
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
    '<polyline points="7 10 12 15 17 10"/>'
    '<line x1="12" y1="15" x2="12" y2="3"/>'
)
ICON_SEARCH = (
    '<circle cx="11" cy="11" r="8"/>'
    '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
)
ICON_ZAPPER = (
    '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
)
ICON_WHATSAPP = (
    '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7'
    ' 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8'
    ' 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5'
    'a8.48 8.48 0 0 1 8 8v.5z"/>'
)
ICON_REFRESH = (
    '<polyline points="23 4 23 10 17 10"/>'
    '<path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>'
)
ICON_RECEIVE = (
    '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'
)
ICON_INFO = (
    '<circle cx="12" cy="12" r="10"/>'
    '<line x1="12" y1="8" x2="12" y2="12"/>'
    '<line x1="12" y1="16" x2="12.01" y2="16"/>'
)
ICON_FOLDER = (
    '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
)
ICON_PRINTER = (
    '<polyline points="6 9 6 2 18 2 18 9"/>'
    '<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>'
    '<rect x="6" y="14" width="12" height="8"/>'
)
ICON_SAVE = (
    '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
    '<polyline points="17 21 17 13 7 13 7 21"/>'
    '<polyline points="7 3 7 8 15 8"/>'
)
ICON_X = (
    '<line x1="18" y1="6" x2="6" y2="18"/>'
    '<line x1="6" y1="6" x2="18" y2="18"/>'
)


def make_action_icon(svg_body: str, size: int = 16, color: str = '#FFFFFF') -> QIcon:
    """Create a simple QIcon for action buttons (single-state, given color)."""
    icon = QIcon()
    icon.addPixmap(_svg_to_pixmap(svg_body, size, color))
    return icon


def set_btn_icon(btn: QPushButton, svg_body: str, size: int = 16,
                 color: str = '#FFFFFF') -> None:
    """Attach an SVG icon to a QPushButton and set its icon size."""
    btn.setIcon(make_action_icon(svg_body, size, color))
    btn.setIconSize(QSize(size, size))


def _svg_to_pixmap(svg_body: str, size: int, color: str) -> QPixmap:
    """Render an SVG path body into a QPixmap of the given square size and stroke color."""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"'
        f' fill="none" stroke="{color}"'
        f' stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f'{svg_body}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    return pixmap


def make_sidebar_icon(svg_body: str, size: int = 18) -> QIcon:
    """Create a dual-state QIcon for sidebar nav items.
    Normal state: muted sidebar text color.  Selected state: white.
    """
    icon = QIcon()
    icon.addPixmap(_svg_to_pixmap(svg_body, size, COLOR_SIDEBAR_TEXT), QIcon.Normal)
    icon.addPixmap(_svg_to_pixmap(svg_body, size, '#FFFFFF'), QIcon.Selected)
    icon.addPixmap(_svg_to_pixmap(svg_body, size, '#FFFFFF'), QIcon.Active)
    return icon


class ScreenHeader(QWidget):
    """Reusable screen header widget: vector icon + bold title + muted subtitle."""

    def __init__(self, icon_svg: str, title: str, subtitle: str = '',
                 font_size: int = 22, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        # Icon + Title on one row
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(10)
        title_row.setAlignment(Qt.AlignVCenter)

        icon_size = max(font_size + 4, 22)
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(icon_size, icon_size)
        icon_lbl.setPixmap(_svg_to_pixmap(icon_svg, icon_size, COLOR_TEXT_PRIMARY))
        icon_lbl.setStyleSheet('background: transparent;')

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f'font-size: {font_size}px; font-weight: 800;'
            f' color: {COLOR_TEXT_PRIMARY}; background: transparent;'
        )

        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        root.addLayout(title_row)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet(
                f'font-size: 13px; color: {COLOR_TEXT_SECONDARY}; background: transparent;'
            )
            sub_lbl.setWordWrap(True)
            root.addWidget(sub_lbl)


class MetricStatCard(QFrame):
    """
    Modern KPI Metric summary card matching the design:
    - Light border, crisp white background
    - Small uppercase label (e.g. 'TOTAL SKUS', 'TOTAL VALUE')
    - Large bold numerical value (e.g. '4,289', '$1.24M')
    """
    def __init__(self, title: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("metricStatCard")
        self.setStyleSheet(f"""
            QFrame#metricStatCard {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 10px 18px;
            }}
        """)
        self.setMinimumWidth(140)
        self.setFixedHeight(72)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignVCenter)

        self.title_label = QLabel(title.upper())
        self.title_label.setStyleSheet(f"""
            color: {COLOR_TEXT_SECONDARY};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: transparent;
        """)
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"""
            color: {COLOR_TEXT_PRIMARY};
            font-size: 22px;
            font-weight: 800;
            background: transparent;
        """)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class StockBadgeDelegate(QStyledItemDelegate):
    """
    Custom delegate for table stock cells to render modern rounded pill badges:
    - Normal stock: Soft Blue background with dark blue text
    - Low stock (<= reorder): Soft Salmon/Pink background with dark red text
    - Zero stock (0): Bold Crimson background with white text
    """
    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Get stock value from model
        text = index.data(Qt.DisplayRole)
        is_low = index.data(Qt.UserRole + 1) # Custom role if provided
        
        try:
            val = int(str(text).replace(",", "").strip())
        except (ValueError, TypeError):
            val = None

        if val is not None:
            if val == 0:
                bg_color = QColor(COLOR_BADGE_ZERO_BG)
                fg_color = QColor(COLOR_BADGE_ZERO_FG)
            elif is_low or val <= 10:
                bg_color = QColor(COLOR_BADGE_LOW_BG)
                fg_color = QColor(COLOR_BADGE_LOW_FG)
            else:
                bg_color = QColor(COLOR_BADGE_NORMAL_BG)
                fg_color = QColor(COLOR_BADGE_NORMAL_FG)

            # Draw centered rounded pill
            rect = option.rect
            badge_width = max(42, len(str(text)) * 9 + 20)
            badge_height = 24
            badge_rect = QRectF(
                rect.x() + (rect.width() - badge_width) / 2,
                rect.y() + (rect.height() - badge_height) / 2,
                badge_width,
                badge_height
            )

            painter.setBrush(QBrush(bg_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(badge_rect, 12, 12)

            painter.setPen(QPen(fg_color))
            font = painter.font()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(badge_rect, Qt.AlignCenter, str(text))
        else:
            super().paint(painter, option, index)

        painter.restore()


def create_primary_action_button(text: str, bg_color: str = COLOR_PRIMARY_RED, hover_color: str = COLOR_PRIMARY_RED_HOVER) -> QPushButton:
    """Helper to create prominent primary action buttons like '+ Stock In' or '+ Add Part'"""
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {bg_color};
            color: #FFFFFF;
            font-weight: 700;
            font-size: 13px;
            border: none;
            border-radius: 6px;
            padding: 8px 18px;
            min-height: 22px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
        QPushButton:pressed {{
            background-color: {hover_color};
        }}
    """)
    return btn


def create_orange_button(text: str) -> QPushButton:
    """Helper to create prominent orange action buttons like 'Create Order'"""
    return create_primary_action_button(text, COLOR_PRIMARY_ORANGE, COLOR_PRIMARY_ORANGE_HOVER)


class QuantityStepper(QWidget):
    """
    Unmistakable quantity stepper control for cart and table rows:
    - High-contrast distinctive '-' (decrease) and '+' (increase) buttons
    - Clear central numeric display
    """
    valueChanged = None  # Defined in __init__ using Signal or custom callback

    def __init__(self, value: int = 1, min_val: int = 1, max_val: int = 100000, parent=None):
        super().__init__(parent)
        self._min_val = min_val
        self._max_val = max_val
        self._value = value
        self._callback = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # Minus button: distinct solid slate button with clear bold minus
        self.minus_btn = QPushButton("−")
        self.minus_btn.setFixedSize(28, 28)
        self.minus_btn.setCursor(Qt.PointingHandCursor)
        self.minus_btn.setToolTip("Decrease Quantity")
        self.minus_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                font-weight: 900;
                font-size: 16px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                border-color: #94A3B8;
                color: #EF4444;
            }
            QPushButton:pressed {
                background-color: #CBD5E1;
            }
        """)
        self.minus_btn.clicked.connect(self._decrement)
        layout.addWidget(self.minus_btn)

        # Quantity label / text box
        self.qty_label = QLabel(str(self._value))
        self.qty_label.setFixedWidth(38)
        self.qty_label.setFixedHeight(28)
        self.qty_label.setAlignment(Qt.AlignCenter)
        self.qty_label.setStyleSheet("""
            QLabel {
                font-weight: 800;
                font-size: 13px;
                color: #0F172A;
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 2px 4px;
            }
        """)
        layout.addWidget(self.qty_label)

        # Plus button: distinct solid slate button with clear bold plus
        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedSize(28, 28)
        self.plus_btn.setCursor(Qt.PointingHandCursor)
        self.plus_btn.setToolTip("Increase Quantity")
        self.plus_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                font-weight: 900;
                font-size: 16px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                border-color: #94A3B8;
                color: #10B981;
            }
            QPushButton:pressed {
                background-color: #CBD5E1;
            }
        """)
        self.plus_btn.clicked.connect(self._increment)
        layout.addWidget(self.plus_btn)

    def set_on_change(self, callback):
        self._callback = callback

    def value(self) -> int:
        return self._value

    def set_value(self, val: int):
        self._value = max(self._min_val, min(self._max_val, val))
        self.qty_label.setText(str(self._value))

    def _decrement(self):
        if self._value > self._min_val:
            self._value -= 1
            self.qty_label.setText(str(self._value))
            if self._callback:
                self._callback(self._value)

    def _increment(self):
        if self._value < self._max_val:
            self._value += 1
            self.qty_label.setText(str(self._value))
            if self._callback:
                self._callback(self._value)


class PlusMinusSpinBox(QWidget):
    """
    A clean, bulletproof spinbox control with explicit '+' (top) and '−' (bottom) buttons.
    Replaces fragile OS QSpinBox arrow subcontrols with unmistakable plus and minus push buttons.
    """
    valueChanged = Signal(int)

    def __init__(self, min_val: int = 1, max_val: int = 100000, value: int = 10, parent=None):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._value = value

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Line edit input
        self.input = QLineEdit(str(self._value))
        self.input.setFixedWidth(54)
        self.input.setFixedHeight(30)
        self.input.setAlignment(Qt.AlignCenter)
        self.input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                color: #0F172A;
                font-weight: 700;
                font-size: 13px;
                border: 1px solid #CBD5E1;
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
                border-right: none;
            }
        """)
        self.input.textChanged.connect(self._on_text_edited)
        layout.addWidget(self.input)

        # Stacked top (+) and bottom (-) buttons
        btn_box = QWidget()
        btn_layout = QVBoxLayout(btn_box)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(0)

        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedSize(24, 15)
        self.plus_btn.setCursor(Qt.PointingHandCursor)
        self.plus_btn.setToolTip("Increase (+)")
        self.plus_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #0F172A;
                font-weight: 900;
                font-size: 11px;
                border: 1px solid #CBD5E1;
                border-top-right-radius: 6px;
                padding: 0px;
                line-height: 11px;
            }
            QPushButton:hover {
                background-color: #FFF7ED;
                color: #F97316;
                border-color: #F97316;
            }
            QPushButton:pressed {
                background-color: #FED7AA;
            }
        """)
        self.plus_btn.clicked.connect(self.increment)
        btn_layout.addWidget(self.plus_btn)

        self.minus_btn = QPushButton("−")
        self.minus_btn.setFixedSize(24, 15)
        self.minus_btn.setCursor(Qt.PointingHandCursor)
        self.minus_btn.setToolTip("Decrease (-)")
        self.minus_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #0F172A;
                font-weight: 900;
                font-size: 11px;
                border: 1px solid #CBD5E1;
                border-top: none;
                border-bottom-right-radius: 6px;
                padding: 0px;
                line-height: 11px;
            }
            QPushButton:hover {
                background-color: #FFF7ED;
                color: #F97316;
                border-color: #F97316;
            }
            QPushButton:pressed {
                background-color: #FED7AA;
            }
        """)
        self.minus_btn.clicked.connect(self.decrement)
        btn_layout.addWidget(self.minus_btn)

        layout.addWidget(btn_box)

    def value(self) -> int:
        return self._value

    def setValue(self, val: int):
        val = max(self._min, min(self._max, val))
        self._value = val
        self.input.blockSignals(True)
        self.input.setText(str(val))
        self.input.blockSignals(False)

    def setRange(self, min_val: int, max_val: int):
        self._min = min_val
        self._max = max_val

    def increment(self):
        self.setValue(self._value + 1)
        self.valueChanged.emit(self._value)

    def decrement(self):
        self.setValue(self._value - 1)
        self.valueChanged.emit(self._value)

    def _on_text_edited(self, text):
        try:
            val = int(text.strip())
            self._value = max(self._min, min(self._max, val))
            self.valueChanged.emit(self._value)
        except ValueError:
            pass
