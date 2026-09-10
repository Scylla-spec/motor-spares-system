"""
Shared base for bulk-import wizards. Excel import and Image/OCR import
(FR-19) both funnel into the same review-and-correct step, the same
edit-sync-before-commit fix, and the same import worker \u2014 only Step 1
(how the raw rows get parsed in the first place) differs between them.
"""
from typing import List, Tuple, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QProgressBar, QStackedWidget, QWidget, QTextEdit
)
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QColor
from utils.excel_importer import import_parts_from_rows
from utils.validators import normalize_part_number, normalize_category


class ImportWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, rows: list):
        super().__init__()
        self.rows = rows

    def run(self):
        try:
            result = import_parts_from_rows(self.rows)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class BaseImportDialog(QDialog):
    """Not used directly \u2014 subclass and implement:
      - self.step1_title, self.dialog_title (strings)
      - _build_step1(self) -> QWidget
      - browse_file(self) -> None (must set self.filepath and update the UI)
      - _parse_and_correct(self) -> Tuple[List[dict], List[str]]
        (raises on hard failure; returns ([], warnings) if nothing usable found)
    """
    import_complete = Signal()  # emitted so inventory screen can refresh

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(900, 600)
        self.filepath = None
        self._preview_data = []
        self._preview_cols = []
        self._worker = None
        self._build_common_ui()

    def _build_common_ui(self):
        layout = QVBoxLayout(self)

        self.step_label = QLabel("")
        self.step_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 6px;")
        layout.addWidget(self.step_label)

        self.pages = QStackedWidget()
        layout.addWidget(self.pages)

        self.pages.addWidget(self._build_step1())
        self.pages.addWidget(self._build_step2())
        self.pages.addWidget(self._build_step3())

        btn_bar = QHBoxLayout()
        self.back_btn = QPushButton("\u25c0  Back")
        self.back_btn.setEnabled(False)
        self.back_btn.clicked.connect(self.go_back)

        self.next_btn = QPushButton("Preview  \u25b6")
        self.next_btn.clicked.connect(self.go_next)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.hide()

        btn_bar.addWidget(self.back_btn)
        btn_bar.addStretch()
        btn_bar.addWidget(self.next_btn)
        btn_bar.addWidget(self.close_btn)
        layout.addLayout(btn_bar)

        self._update_step_label(0)

    # ---- Step 1: subclass-specific (file picker + source-specific parsing) ----
    def _build_step1(self) -> QWidget:
        raise NotImplementedError

    def browse_file(self):
        raise NotImplementedError

    def _parse_and_correct(self) -> Tuple[List[Dict[str, Any]], List[str]]:
        raise NotImplementedError

    # ---- Step 2: review table (shared) ----
    def _build_step2(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        legend = QHBoxLayout()
        for colour, label in [("#d4edda", "OK"), ("#fff3cd", "Auto-corrected"), ("#f8d7da", "Error \u2014 will be skipped")]:
            swatch = QLabel(f"  {label}  ")
            swatch.setStyleSheet(f"background-color: {colour}; border: 1px solid #ccc; padding: 2px;")
            legend.addWidget(swatch)
        legend.addStretch()
        layout.addLayout(legend)

        hint = QLabel("Cells below are editable \u2014 correct anything before importing.")
        hint.setStyleSheet("color: #555; font-style: italic;")
        layout.addWidget(hint)

        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.preview_table)

        return w

    # ---- Step 3: result (shared) ----
    def _build_step3(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)

        return w

    # ---- Navigation (shared) ----
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
            self._update_step_label(page - 1)

    def _update_step_label(self, page):
        labels = [
            self.step1_title,
            "Step 2 of 3 \u2014 Review & correct data",
            "Step 3 of 3 \u2014 Import complete"
        ]
        self.step_label.setText(labels[page])

    # ---- Preview (shared) ----
    def _load_preview(self):
        if not self.filepath:
            QMessageBox.warning(self, "No File", "Please select a file first.")
            return

        try:
            corrected, warnings = self._parse_and_correct()
        except Exception as e:
            QMessageBox.critical(self, "Read Error", f"Could not read file:\n{e}")
            return

        if not corrected:
            QMessageBox.warning(self, "No Data Found", "\n".join(warnings) if warnings else "No data rows found.")
            return

        self._preview_data = corrected
        self._populate_preview_table()

        if warnings:
            QMessageBox.information(self, "Notes", "\n".join(warnings))

        self.pages.setCurrentIndex(1)
        self.back_btn.setEnabled(True)
        self.next_btn.setText("Import Now  \u25b6")
        self._update_step_label(1)

    def _populate_preview_table(self):
        COLS = ["part_number", "name", "category", "brand",
                "cost_price", "selling_price", "quantity_on_hand", "reorder_level", "Notes"]
        self._preview_cols = COLS
        self.preview_table.setColumnCount(len(COLS))
        self.preview_table.setHorizontalHeaderLabels([c.replace("_", " ").title() for c in COLS])
        self.preview_table.setRowCount(len(self._preview_data))

        for row_idx, row in enumerate(self._preview_data):
            has_error = bool(row.get("_errors"))
            # A row is yellow if it has auto-corrections OR warnings (e.g. missing
            # part number / name that the user needs to fill in).
            has_attention = bool(row.get("_corrections")) or bool(row.get("_warnings"))

            if has_error:
                bg = QColor("#f8d7da")
            elif has_attention:
                bg = QColor("#fff3cd")
            else:
                bg = QColor("#d4edda")

            notes = []
            notes += [f"[CORRECTED] {c}" for c in row.get("_corrections", [])]
            notes += [f"[WARNING] {w}" for w in row.get("_warnings", [])]
            notes += [f"[ERROR] {e}" for e in row.get("_errors", [])]

            for col_idx, field in enumerate(COLS):
                if field == "Notes":
                    value = " | ".join(notes) if notes else "OK"
                else:
                    value = str(row.get(field, "") or "")
                item = QTableWidgetItem(value)
                item.setBackground(bg)
                self.preview_table.setItem(row_idx, col_idx, item)

    # ---- Import (shared) ----
    def _sync_edits_from_table(self):
        """Reads whatever is currently in the editable preview cells back
        into self._preview_data before import, so corrections the user
        typed (fixing an OCR misread, a bad Excel cell, etc.) actually get
        used \u2014 not just displayed and then silently discarded."""
        for row_idx, row in enumerate(self._preview_data):
            for col_idx, field in enumerate(self._preview_cols):
                if field == "Notes":
                    continue
                item = self.preview_table.item(row_idx, col_idx)
                if item is None:
                    continue
                text = item.text().strip()

                if field in ("cost_price", "selling_price"):
                    try:
                        row[field] = float(text) if text else 0.0
                    except ValueError:
                        pass
                elif field in ("quantity_on_hand", "reorder_level"):
                    try:
                        row[field] = int(float(text)) if text else 0
                    except ValueError:
                        pass
                elif field == "part_number":
                    row[field] = normalize_part_number(text)
                elif field == "category":
                    row[field] = normalize_category(text)
                else:
                    row[field] = text.upper()

            # Re-validate after edits. Only truly unrecoverable issues
            # (negative price) become hard errors that block import.
            # Missing part_number or name become warnings so the user can
            # still fill them in during review and proceed.
            errors = []
            if row.get("cost_price", 0) < 0:
                errors.append("Cost price cannot be negative.")
            if row.get("selling_price", 0) <= 0:
                errors.append("Selling price must be greater than 0.")
            row["_errors"] = errors

            # Refresh warnings for still-missing required-ish fields
            existing_warns = [
                w for w in row.get("_warnings", [])
                if "Part Number was missing" not in w and "Name is missing" not in w
            ]
            if not row.get("part_number"):
                existing_warns.append(
                    "Part Number is blank — please fill it in before importing."
                )
            if not row.get("name"):
                existing_warns.append(
                    "Name is blank — please fill it in before importing."
                )
            row["_warnings"] = existing_warns

    def _run_import(self):
        self._sync_edits_from_table()

        self.pages.setCurrentIndex(2)
        self.next_btn.hide()
        self.back_btn.setEnabled(False)
        self.progress_bar.show()
        self._update_step_label(2)
        self.result_text.setPlainText("Importing... please wait.")

        self._worker = ImportWorker(self._preview_data)
        self._worker.finished.connect(self._on_import_done)
        self._worker.error.connect(self._on_import_error)
        self._worker.start()

    def _on_import_done(self, result: dict):
        self.progress_bar.hide()
        imported = result["imported"]
        merged = result.get("merged", 0)
        skipped = result["skipped"]
        warnings = result.get("warnings", [])
        errors = result.get("errors", [])

        summary = [
            "Import complete!",
            "",
            f"  Rows added as new:        {imported}",
            f"  Rows merged into existing: {merged}",
            f"  Rows skipped:              {skipped}",
            "",
        ]
        if warnings:
            summary.append("\u2500\u2500 Auto-corrections & Warnings \u2500\u2500")
            summary += [f"  {w}" for w in warnings]
            summary.append("")
        if errors:
            summary.append("\u2500\u2500 Errors (rows skipped) \u2500\u2500")
            summary += [f"  {e}" for e in errors]

        self.result_text.setPlainText("\n".join(summary))
        self.close_btn.show()

        if imported > 0:
            self.import_complete.emit()

    def _on_import_error(self, msg: str):
        self.progress_bar.hide()
        self.result_text.setPlainText(f"ERROR during import:\n\n{msg}")
        self.back_btn.setEnabled(True)
        self.next_btn.show()
        self.next_btn.setText("Retry  \u25b6")
