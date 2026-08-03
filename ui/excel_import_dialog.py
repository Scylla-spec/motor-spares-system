"""
Excel Import Dialog — Step-by-step wizard for bulk importing parts from .xlsx files.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QProgressBar, QStackedWidget, QWidget, QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from utils.excel_importer import parse_excel_file, auto_correct_rows, import_parts_from_excel


# ---------------------------------------------------------------------------
# Background Worker Thread (keeps UI responsive during import)
# ---------------------------------------------------------------------------
class ImportWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            result = import_parts_from_excel(self.filepath)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Main Dialog
# ---------------------------------------------------------------------------
class ExcelImportDialog(QDialog):
    import_complete = Signal()  # emitted so inventory screen can refresh

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Import Parts from Excel")
        self.setMinimumSize(900, 600)
        self.filepath = None
        self._preview_data = []
        self._worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Step indicator
        self.step_label = QLabel("Step 1 of 3 — Select your Excel file")
        self.step_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 6px;")
        layout.addWidget(self.step_label)

        # Stacked pages
        self.pages = QStackedWidget()
        layout.addWidget(self.pages)

        self.pages.addWidget(self._build_step1())
        self.pages.addWidget(self._build_step2())
        self.pages.addWidget(self._build_step3())

        # Navigation buttons
        btn_bar = QHBoxLayout()
        self.back_btn = QPushButton("◀  Back")
        self.back_btn.setEnabled(False)
        self.back_btn.clicked.connect(self.go_back)

        self.next_btn = QPushButton("Preview  ▶")
        self.next_btn.clicked.connect(self.go_next)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.hide()

        btn_bar.addWidget(self.back_btn)
        btn_bar.addStretch()
        btn_bar.addWidget(self.next_btn)
        btn_bar.addWidget(self.close_btn)
        layout.addLayout(btn_bar)

    # ------------------------------------------------------------------ Step 1
    def _build_step1(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addStretch()

        info = QLabel(
            "<h3>📂 Select an Excel File (.xlsx)</h3>"
            "<p>The importer recognises a wide variety of column name formats. "
            "Required columns: <b>Part Number</b> and <b>Name</b>.</p>"
            "<p>Optional columns: Category, Brand, Compatible Vehicles, "
            "Cost Price, Selling Price, Quantity, Reorder Level, Supplier.</p>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.file_label = QLabel("No file selected.")
        self.file_label.setStyleSheet("color: grey; padding: 8px;")
        layout.addWidget(self.file_label)

        browse_btn = QPushButton("📂  Browse for Excel File...")
        browse_btn.setMinimumHeight(40)
        browse_btn.clicked.connect(self.browse_file)
        layout.addWidget(browse_btn)

        layout.addStretch()
        return w

    # ------------------------------------------------------------------ Step 2
    def _build_step2(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        legend = QHBoxLayout()
        for colour, label in [("#d4edda", "OK"), ("#fff3cd", "Auto-corrected"), ("#f8d7da", "Error — will be skipped")]:
            swatch = QLabel(f"  {label}  ")
            swatch.setStyleSheet(f"background-color: {colour}; border: 1px solid #ccc; padding: 2px;")
            legend.addWidget(swatch)
        legend.addStretch()
        layout.addLayout(legend)

        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.preview_table)

        return w

    # ------------------------------------------------------------------ Step 3
    def _build_step3(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)

        return w

    # ------------------------------------------------------------------ Navigation
    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)"
        )
        if path:
            self.filepath = path
            short = path.split("\\")[-1]
            self.file_label.setText(f"✅  {short}")
            self.file_label.setStyleSheet("color: green; padding: 8px;")

    def go_next(self):
        page = self.pages.currentIndex()
        if page == 0:
            self._load_preview()
        elif page == 1:
            self._run_import()

    def go_back(self):
        page = self.pages.currentIndex()
        if page > 0:
            self.pages.setCurrentIndex(page - 1)
            self.back_btn.setEnabled(page - 1 > 0)
            self.next_btn.show()
            self.close_btn.hide()
            self._update_step_label(page)

    def _update_step_label(self, page):
        labels = [
            "Step 1 of 3 — Select your Excel file",
            "Step 2 of 3 — Review & correct data",
            "Step 3 of 3 — Import complete"
        ]
        self.step_label.setText(labels[page])

    # ------------------------------------------------------------------ Preview
    def _load_preview(self):
        if not self.filepath:
            QMessageBox.warning(self, "No File", "Please select an Excel file first.")
            return

        try:
            raw_rows, parse_warnings = parse_excel_file(self.filepath)
        except Exception as e:
            QMessageBox.critical(self, "Read Error", f"Could not read file:\n{e}")
            return

        if not raw_rows:
            QMessageBox.warning(self, "Empty File", "No data rows found in the selected file.")
            return

        self._preview_data = auto_correct_rows(raw_rows)
        self._populate_preview_table()

        if parse_warnings:
            QMessageBox.warning(self, "Column Mapping Warnings", "\n".join(parse_warnings))

        self.pages.setCurrentIndex(1)
        self.back_btn.setEnabled(True)
        self.next_btn.setText("Import Now  ▶")
        self._update_step_label(1)

    def _populate_preview_table(self):
        COLS = ["part_number", "name", "category", "brand",
                "cost_price", "selling_price", "quantity_on_hand", "reorder_level", "Notes"]
        self.preview_table.setColumnCount(len(COLS))
        self.preview_table.setHorizontalHeaderLabels([c.replace("_", " ").title() for c in COLS])
        self.preview_table.setRowCount(len(self._preview_data))

        for row_idx, row in enumerate(self._preview_data):
            has_error = bool(row.get("_errors"))
            has_correction = bool(row.get("_corrections"))

            if has_error:
                bg = QColor("#f8d7da")
            elif has_correction:
                bg = QColor("#fff3cd")
            else:
                bg = QColor("#d4edda")

            notes = []
            notes += [f"✏ {c}" for c in row.get("_corrections", [])]
            notes += [f"⚠ {w}" for w in row.get("_warnings", [])]
            notes += [f"❌ {e}" for e in row.get("_errors", [])]

            for col_idx, field in enumerate(COLS):
                if field == "Notes":
                    value = " | ".join(notes) if notes else "✅ OK"
                else:
                    value = str(row.get(field, "") or "")
                item = QTableWidgetItem(value)
                item.setBackground(bg)
                self.preview_table.setItem(row_idx, col_idx, item)

    # ------------------------------------------------------------------ Import
    def _run_import(self):
        self.pages.setCurrentIndex(2)
        self.next_btn.hide()
        self.back_btn.setEnabled(False)
        self.progress_bar.show()
        self._update_step_label(2)
        self.result_text.setPlainText("Importing... please wait.")

        self._worker = ImportWorker(self.filepath)
        self._worker.finished.connect(self._on_import_done)
        self._worker.error.connect(self._on_import_error)
        self._worker.start()

    def _on_import_done(self, result: dict):
        self.progress_bar.hide()
        imported = result["imported"]
        skipped = result["skipped"]
        warnings = result.get("warnings", [])
        errors = result.get("errors", [])

        summary = [
            f"✅  Import complete!",
            f"",
            f"  Rows imported:  {imported}",
            f"  Rows skipped:   {skipped}",
            f"",
        ]
        if warnings:
            summary.append("── Auto-corrections & Warnings ──")
            summary += [f"  {w}" for w in warnings]
            summary.append("")
        if errors:
            summary.append("── Errors (rows skipped) ──")
            summary += [f"  {e}" for e in errors]

        self.result_text.setPlainText("\n".join(summary))
        self.close_btn.show()

        if imported > 0:
            self.import_complete.emit()

    def _on_import_error(self, msg: str):
        self.progress_bar.hide()
        self.result_text.setPlainText(f"❌ Unexpected error during import:\n\n{msg}")
        self.back_btn.setEnabled(True)
        self.next_btn.show()
        self.next_btn.setText("Retry  ▶")
