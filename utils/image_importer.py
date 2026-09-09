"""
Image (OCR) Bulk Import Utility (FR-19)
========================================
Extracts part data from a photograph of a document — a supplier price
list, invoice, or handwritten stock sheet — using offline OCR
(pytesseract), and feeds it through the exact same auto-correction and
review pipeline already built for Excel import (utils/excel_importer.py).

Scope, deliberately: this reads photographed DOCUMENTS (text), not
photographs of physical parts. Visual part recognition from a photo of
the item itself is a materially different, much larger computer-vision
feature and is out of scope here — see Section 4.1 of the v2 planning
doc for the reasoning.

Requires the Tesseract OCR engine to be installed on the machine
(a system binary, not just a pip package — see README for install
instructions per OS). Everything else runs fully offline, no cloud
OCR service involved.

If Tesseract is not installed, this module degrades gracefully:
TESSERACT_AVAILABLE will be False and is_tesseract_available() returns
False. All public functions return a friendly error string rather than
crashing.
"""
import re
import logging
from typing import List, Dict, Any, Tuple

from PIL import Image, ImageOps

from utils.excel_importer import COLUMN_ALIASES, _normalise, auto_correct_rows

import os
import shutil
import platform

# ---------------------------------------------------------------------------
# Tesseract availability check — cross-platform auto-detection (Windows, macOS, Linux)
# ---------------------------------------------------------------------------
TESSERACT_AVAILABLE: bool = False
TESSERACT_ERROR: str = ""

try:
    import pytesseract
    from pytesseract import Output

    # Check standard paths across Windows, macOS, Linux if not already in system PATH
    _candidate_paths = [
        os.environ.get("TESSERACT_PATH", ""),
        shutil.which("tesseract") or "",
        # Windows standard locations
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        # macOS standard locations (Homebrew / Intel / Apple Silicon)
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
        # Linux standard locations
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for _path in _candidate_paths:
        if _path and os.path.exists(_path):
            pytesseract.pytesseract.tesseract_cmd = _path
            break

    # Lightweight check: ask for version without touching any image.
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except Exception as _tess_err:
    TESSERACT_AVAILABLE = False
    TESSERACT_ERROR = str(_tess_err)
    logging.warning(f"Tesseract OCR not available: {_tess_err}")


def _build_tesseract_install_guide() -> str:
    """Returns OS-appropriate installation instructions for Tesseract OCR."""
    sys_name = platform.system()
    if sys_name == "Darwin":
        return (
            "Tesseract OCR is not installed on this macOS system.\n\n"
            "To enable image import, install it using Homebrew:\n\n"
            "    brew install tesseract\n\n"
            "After installing, restart the Motor Spares System and try again."
        )
    elif sys_name == "Linux":
        return (
            "Tesseract OCR is not installed on this Linux system.\n\n"
            "To enable image import, install it using your package manager:\n\n"
            "  Ubuntu / Debian:\n"
            "    sudo apt update && sudo apt install tesseract-ocr\n\n"
            "  Fedora / RHEL:\n"
            "    sudo dnf install tesseract\n\n"
            "  Arch Linux:\n"
            "    sudo pacman -S tesseract\n\n"
            "After installing, restart the Motor Spares System and try again."
        )
    else:
        return (
            "Tesseract OCR is not installed on this computer.\n\n"
            "To enable image import, install it using ONE of these methods:\n\n"
            "  Option 1 — Windows Package Manager (recommended):\n"
            "    Open a terminal and run:\n"
            "    winget install UB-Mannheim.TesseractOCR\n\n"
            "  Option 2 — Direct installer:\n"
            "    Download from: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "    Run the installer, then restart this application.\n\n"
            "After installing, restart the Motor Spares System and try again."
        )


# Install instructions shown to the user when Tesseract is missing
TESSERACT_INSTALL_GUIDE: str = _build_tesseract_install_guide()


def is_tesseract_available() -> bool:
    """Returns True if Tesseract is installed and reachable."""
    return TESSERACT_AVAILABLE


# Fields we can plausibly extract from a photographed price list / invoice.
# Same canonical set as Excel import, so auto_correct_rows() works unchanged.
_KNOWN_FIELDS = list(COLUMN_ALIASES.keys())


def _preprocess_image(filepath: str) -> Image.Image:
    """Basic preprocessing to improve OCR accuracy on a phone photo:
    grayscale + auto-contrast. Deliberately conservative — aggressive
    thresholding tends to hurt accuracy on photos taken at an angle or
    in uneven light more than it helps.
    """
    img = Image.open(filepath)
    img = ImageOps.exif_transpose(img)  # respect phone camera orientation
    img = img.convert("L")  # grayscale
    img = ImageOps.autocontrast(img)
    return img


def _extract_lines_by_position(img: Image.Image) -> List[List[str]]:
    """Extracts text grouped into visual lines and columns using Tesseract's
    per-word bounding boxes (image_to_data), instead of image_to_string's
    plain text.

    This matters because image_to_string collapses any run of whitespace
    — including a wide gap between printed table columns — down to a
    single space, so splitting on '2+ spaces' almost never finds real
    column boundaries in a photographed table. Working from word
    positions instead lets us reconstruct columns based on actual gaps
    on the page, which survives that collapsing.

    Returns a list of lines, each a list of field strings (one per
    detected column).
    """
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    n = len(data["text"])

    # Group words into lines using Tesseract's own line grouping
    # (block_num, par_num, line_num), which is robust to slight vertical
    # jitter that a raw y-coordinate grouping would mis-handle.
    lines: Dict[Tuple[int, int, int], List[dict]] = {}
    for i in range(n):
        word = data["text"][i].strip()
        if not word:
            continue
        conf = data["conf"][i]
        try:
            if float(conf) < 0:  # -1 marks non-text regions
                continue
        except (TypeError, ValueError):
            pass
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append({
            "text": word,
            "left": data["left"][i],
            "width": data["width"][i],
            "height": data["height"][i],
        })

    result_lines = []
    for key in sorted(lines.keys()):
        words = sorted(lines[key], key=lambda w: w["left"])
        if not words:
            continue

        # A gap counts as a new column once it's noticeably wider than a
        # typical space between words on this line — proportional to
        # text height so it scales with the photo's resolution/zoom.
        avg_height = sum(w["height"] for w in words) / len(words)
        column_gap_threshold = max(avg_height * 1.2, 20)

        fields = []
        current_field_words = [words[0]["text"]]
        prev_right = words[0]["left"] + words[0]["width"]

        for w in words[1:]:
            gap = w["left"] - prev_right
            if gap > column_gap_threshold:
                fields.append(" ".join(current_field_words))
                current_field_words = [w["text"]]
            else:
                current_field_words.append(w["text"])
            prev_right = w["left"] + w["width"]

        fields.append(" ".join(current_field_words))
        result_lines.append(fields)

    return result_lines


def _map_line_to_fields(headers: List[str]) -> Dict[str, int]:
    """Same header-matching logic as Excel import, reused so a
    photographed table with a recognisable header row maps the same way
    a spreadsheet would."""
    mapping = {}
    normalised = [_normalise(h) for h in headers]
    for field, aliases in COLUMN_ALIASES.items():
        for idx, header in enumerate(normalised):
            if header in aliases or any(a in header for a in aliases):
                mapping[field] = idx
                break
    return mapping


def parse_image_file(filepath: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Runs OCR on a photographed document and returns:
    - list of raw row dicts with canonical field names (best-effort)
    - list of warnings, including an explicit one about OCR reliability

    Unlike Excel import, this can't guarantee reliable column detection
    — OCR text rarely lines up as cleanly as real spreadsheet cells.
    Every row is expected to be reviewed/corrected in the review dialog
    before committing, same as Excel import.

    Returns ([], [error_message]) if Tesseract is not installed, so
    callers always receive a well-formed result rather than an exception.
    """
    if not TESSERACT_AVAILABLE:
        return [], [TESSERACT_INSTALL_GUIDE]

    warnings = [
        "OCR results are approximate — please review every row below "
        "before importing, especially prices and quantities."
    ]

    try:
        img = _preprocess_image(filepath)
        lines = _extract_lines_by_position(img)
    except Exception as e:
        logging.error(f"OCR failed for {filepath}: {e}")
        return [], [f"Could not read text from this image: {e}"]

    if not lines:
        return [], ["No readable text was found in this image. Try a clearer, "
                     "better-lit photo taken straight-on."]

    # Does the first line look like a header row? (contains recognised
    # column-name words rather than looking like a data row)
    header_map = _map_line_to_fields(lines[0]) if len(lines[0]) >= 2 else {}
    has_header = len(header_map) >= 2  # need at least 2 recognised columns to trust it

    data_lines = lines[1:] if has_header else lines
    if not has_header:
        warnings.append(
            "Could not confidently detect a header row, so columns could not "
            "be auto-mapped. Every field below will need manual review — "
            "only the raw text per line was captured."
        )

    parsed_rows = []
    for fields in data_lines:
        if not fields:
            continue

        record = {}
        if has_header:
            for field, col_idx in header_map.items():
                record[field] = fields[col_idx] if col_idx < len(fields) else None
        elif len(fields) >= 2:
            # No header to map against, but we still detected multiple
            # columns from spacing — best-effort positional guess using
            # the same left-to-right order most price lists use.
            guess_order = ["part_number", "name", "category", "cost_price", "selling_price", "quantity_on_hand"]
            for idx, value in enumerate(fields[:len(guess_order)]):
                record[guess_order[idx]] = value
        else:
            # Only one column detected — nothing reliable to split, so
            # the whole line goes into 'name' so nothing is silently lost;
            # the reviewer fills in the rest.
            record["name"] = fields[0]

        parsed_rows.append(record)

    return parsed_rows, warnings


def import_image_preview(filepath: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse + auto-correct, ready for the review dialog. Mirrors the
    Excel import pipeline's parse → auto_correct_rows steps, stopping
    short of committing anything — that happens via
    utils.excel_importer.import_parts_from_rows() after the user reviews.

    Returns ([], [error_message]) if Tesseract is not installed.
    """
    if not TESSERACT_AVAILABLE:
        return [], [TESSERACT_INSTALL_GUIDE]

    raw_rows, warnings = parse_image_file(filepath)
    if not raw_rows:
        return [], warnings
    corrected = auto_correct_rows(raw_rows)
    return corrected, warnings
