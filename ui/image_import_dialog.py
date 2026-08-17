"""
Image (OCR) Import Dialog — Step-by-step wizard for bulk importing parts
from a photograph of a document (FR-19).

Built on ui.base_import_dialog.BaseImportDialog, which supplies the
shared review-table / edit-before-commit / background-import steps
already proven out by Excel import. Only Step 1 (picking a photo and
running OCR on it) is specific to this dialog.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QFrame
)
from PySide6.QtCore import Qt
from ui.base_import_dialog import BaseImportDialog
from utils.image_importer import import_image_preview, is_tesseract_available, TESSERACT_INSTALL_GUIDE


class ImageImportDialog(BaseImportDialog):
    def __init__(self, parent=None):
        self.step1_title = "Step 1 of 3 — Select a photo of your price list / invoice"
        super().__init__(parent)
        self.setWindowTitle("Bulk Import Parts from a Photo")

    # ---- Step 1: photo picker ----
    def _build_step1(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addStretch()

        tess_ok = is_tesseract_available()

        if not tess_ok:
            # ---- Tesseract missing: show clear install instructions ----
            warn_frame = QFrame()
            warn_frame.setStyleSheet(
                "QFrame { background-color: #fff3cd; border: 2px solid #ffc107; border-radius: 6px; padding: 10px; }"
            )
            warn_layout = QVBoxLayout(warn_frame)

            title_lbl = QLabel("[!]  Tesseract OCR is not installed")
            title_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #856404;")
            warn_layout.addWidget(title_lbl)

            guide_lbl = QLabel(TESSERACT_INSTALL_GUIDE)
            guide_lbl.setWordWrap(True)
            guide_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            guide_lbl.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 11px; color: #333; padding-top: 6px;"
            )
            warn_layout.addWidget(guide_lbl)

            layout.addWidget(warn_frame)
        else:
            # ---- Normal info text when Tesseract is available ----
            info = QLabel(
                "<h3>Select a Photo (.jpg, .png)</h3>"
                "<p>Works best with a supplier price list, invoice, or stock sheet "
                "photographed straight-on, in good light.</p>"
                "<p>OCR reads the text automatically, but results are approximate — "
                "you'll review and correct every row before anything is imported, "
                "exactly like Excel import.</p>"
                "<p><b>No specific column format is required.</b> Any text the OCR "
                "can read is surfaced in the review table for you to confirm or correct.</p>"
            )
            info.setWordWrap(True)
            layout.addWidget(info)

        self.file_label = QLabel("No photo selected.")
        self.file_label.setStyleSheet("color: grey; padding: 8px;")
        layout.addWidget(self.file_label)

        self.browse_photo_btn = QPushButton("Browse for Photo...")
        self.browse_photo_btn.setMinimumHeight(40)
        self.browse_photo_btn.clicked.connect(self.browse_file)
        # Disable browse if Tesseract isn't available — nothing to process
        self.browse_photo_btn.setEnabled(tess_ok)
        if not tess_ok:
            self.browse_photo_btn.setToolTip("Install Tesseract OCR first (see instructions above).")
        layout.addWidget(self.browse_photo_btn)

        layout.addStretch()
        return w

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Photo", "", "Images (*.jpg *.jpeg *.png)"
        )
        if path:
            self.filepath = path
            short = path.split("/")[-1].split("\\")[-1]
            self.file_label.setText(f"[OK]  {short}")
            self.file_label.setStyleSheet("color: green; padding: 8px;")

    # ---- Step 1 -> Step 2: parse via OCR + auto-correct ----
    def _parse_and_correct(self):
        return import_image_preview(self.filepath)
