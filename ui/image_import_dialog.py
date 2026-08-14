"""
Image (OCR) Import Dialog — Step-by-step wizard for bulk importing parts
from a photograph of a document (FR-19).

Built on ui.base_import_dialog.BaseImportDialog, which supplies the
shared review-table / edit-before-commit / background-import steps
already proven out by Excel import. Only Step 1 (picking a photo and
running OCR on it) is specific to this dialog.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog
from ui.base_import_dialog import BaseImportDialog
from utils.image_importer import import_image_preview


class ImageImportDialog(BaseImportDialog):
    def __init__(self, parent=None):
        self.step1_title = "Step 1 of 3 \u2014 Select a photo of your price list / invoice"
        super().__init__(parent)
        self.setWindowTitle("Bulk Import Parts from a Photo")

    # ---- Step 1: photo picker ----
    def _build_step1(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addStretch()

        info = QLabel(
            "<h3>\U0001F4F7 Select a Photo (.jpg, .png)</h3>"
            "<p>Works best with a supplier price list, invoice, or stock sheet "
            "photographed straight-on, in good light.</p>"
            "<p>OCR reads the text automatically, but results are approximate \u2014 "
            "you'll review and correct every row before anything is imported, "
            "exactly like Excel import.</p>"
            "<p><i>Requires the Tesseract OCR engine to be installed on this "
            "computer (a one-time system install \u2014 see the app's README).</i></p>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.file_label = QLabel("No photo selected.")
        self.file_label.setStyleSheet("color: grey; padding: 8px;")
        layout.addWidget(self.file_label)

        browse_btn = QPushButton("\U0001F4C2  Browse for Photo...")
        browse_btn.setMinimumHeight(40)
        browse_btn.clicked.connect(self.browse_file)
        layout.addWidget(browse_btn)

        layout.addStretch()
        return w

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Photo", "", "Images (*.jpg *.jpeg *.png)"
        )
        if path:
            self.filepath = path
            short = path.split("/")[-1].split("\\")[-1]
            self.file_label.setText(f"\u2705  {short}")
            self.file_label.setStyleSheet("color: green; padding: 8px;")

    # ---- Step 1 -> Step 2: parse via OCR + auto-correct ----
    def _parse_and_correct(self):
        return import_image_preview(self.filepath)
