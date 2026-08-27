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
from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen

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

/* SpinBox & DateEdit with clean, clear up/down arrow buttons */
QSpinBox, QDoubleSpinBox, QDateEdit {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 4px 28px 4px 8px;
    min-height: 24px;
    font-size: 13px;
}}

QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 1px solid {COLOR_PRIMARY_ORANGE};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    height: 14px;
    border-left: 1px solid #CBD5E1;
    border-bottom: 1px solid #E2E8F0;
    border-top-right-radius: 5px;
    background-color: #F1F5F9;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: #E2E8F0;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    height: 14px;
    border-left: 1px solid #CBD5E1;
    border-bottom-right-radius: 5px;
    background-color: #F1F5F9;
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: #E2E8F0;
}}

QDateEdit::drop-down {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #CBD5E1;
    background-color: #F1F5F9;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
}}

QDateEdit::drop-down:hover {{
    background-color: #E2E8F0;
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
