"""
Thermal Receipt Generator and Printer for Motor Spares System.
Supports standard 80mm (48-column) and 58mm (32-column) POS receipt rolls.
Sends raw ESC/POS commands directly via the Windows Spooler (win32print / winspool),
ensuring compatibility with all USB, Network, and Bluetooth thermal receipt printers
(Epson, Xprinter, Bixolon, Star, Rongta, GOOJPRT, Generic / Text Only, etc.).
"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Tuple, Optional
from models.sale import Sale
from managers.settings_manager import get_all_settings

RECEIPTS_DIR = "receipts"

# --- ESC/POS Command Constants ---
ESC = b'\x1b'
GS = b'\x1d'

CMD_INIT = ESC + b'@'                     # Initialize printer
CMD_ALIGN_LEFT = ESC + b'a\x00'           # Left justify
CMD_ALIGN_CENTER = ESC + b'a\x01'         # Center justify
CMD_ALIGN_RIGHT = ESC + b'a\x02'          # Right justify
CMD_BOLD_ON = ESC + b'E\x01'              # Bold on
CMD_BOLD_OFF = ESC + b'E\x00'             # Bold off
CMD_DOUBLE_SIZE = GS + b'!\x11'           # Double height & width
CMD_DOUBLE_HEIGHT = GS + b'!\x01'         # Double height
CMD_NORMAL_SIZE = GS + b'!\x00'           # Normal font size
CMD_FEED_CUT = b'\n\n\n\n' + GS + b'V\x00' # Feed 4 lines and full paper cut
CMD_PARTIAL_CUT = b'\n\n\n\n' + GS + b'V\x01' # Partial cut
CMD_DRAWER_KICK = ESC + b'p\x00\x19\xfa'  # Pulse cash drawer kick pin 2


def get_available_printers() -> List[str]:
    """Returns a list of all printer names installed on this Windows system."""
    printers = []
    # 1. Try win32print
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        for p in win32print.EnumPrinters(flags):
            printers.append(p[2])
        if printers:
            return sorted(list(set(printers)))
    except Exception as e:
        logging.debug(f"win32print printer enumeration: {e}")

    # 2. Try PySide6 QPrinterInfo
    try:
        from PySide6.QtPrintSupport import QPrinterInfo
        qt_printers = QPrinterInfo.availablePrinterNames()
        if qt_printers:
            return sorted(list(set(qt_printers)))
    except Exception as e:
        logging.debug(f"QPrinterInfo printer enumeration: {e}")

    return printers


def _send_raw_to_printer(printer_name: str, data: bytes, doc_name: str = "POS Thermal Receipt") -> Tuple[bool, str]:
    """
    Sends raw bytes directly to a Windows printer spooler.
    Tries win32print first, then ctypes winspool.drv.
    """
    if not printer_name or not printer_name.strip():
        return False, "No printer specified."

    # Method 1: win32print
    try:
        import win32print
        h_printer = win32print.OpenPrinter(printer_name)
        try:
            h_job = win32print.StartDocPrinter(h_printer, 1, (doc_name, None, "RAW"))
            try:
                win32print.StartPagePrinter(h_printer)
                win32print.WritePrinter(h_printer, data)
                win32print.EndPagePrinter(h_printer)
            finally:
                win32print.EndDocPrinter(h_printer)
        finally:
            win32print.ClosePrinter(h_printer)
        return True, f"Printed successfully on '{printer_name}'."
    except Exception as e1:
        logging.warning(f"win32print failed for '{printer_name}': {e1}. Trying ctypes fallback...")

    # Method 2: ctypes winspool.drv fallback
    try:
        import ctypes
        from ctypes import wintypes

        winspool = ctypes.WinDLL("winspool.drv")

        class DOC_INFO_1W(ctypes.Structure):
            _fields_ = [
                ("pDocName", wintypes.LPWSTR),
                ("pOutputFile", wintypes.LPWSTR),
                ("pDatatype", wintypes.LPWSTR),
            ]

        h_printer = wintypes.HANDLE()
        if not winspool.OpenPrinterW(printer_name, ctypes.byref(h_printer), None):
            return False, f"Could not open printer '{printer_name}' via Windows Spooler."

        try:
            doc_info = DOC_INFO_1W(doc_name, None, "RAW")
            job_id = winspool.StartDocPrinterW(h_printer, 1, ctypes.byref(doc_info))
            if job_id == 0:
                return False, f"Could not start print document on '{printer_name}'."

            try:
                winspool.StartPagePrinter(h_printer)
                written = wintypes.DWORD()
                winspool.WritePrinter(h_printer, data, len(data), ctypes.byref(written))
                winspool.EndPagePrinter(h_printer)
            finally:
                winspool.EndDocPrinter(h_printer)
        finally:
            winspool.ClosePrinter(h_printer)

        return True, f"Printed successfully on '{printer_name}'."
    except Exception as e2:
        logging.error(f"ctypes winspool failed for '{printer_name}': {e2}")
        return False, f"Printer error: {e2}"


def _format_supermarket_text(
    settings: dict,
    receipt_number: str,
    date_str: str,
    cashier_name: str,
    customer_name: str,
    items: list,
    total_amount: float,
    payment_method: str,
    width_chars: int = 48
) -> str:
    """
    Formats the receipt as a clean monospaced plain-text string,
    perfect for 80mm (48 chars wide) or 58mm (32 chars wide).
    """
    w = width_chars
    lines = []

    def center(text: str) -> str:
        return text.strip().center(w)[:w]

    def divider(char: str = "-") -> str:
        return char * w

    def key_val(key: str, val: str) -> str:
        space = w - len(key) - len(val)
        if space < 1:
            return f"{key} {val}"[:w]
        return f"{key}{' ' * space}{val}"

    # Header
    shop_name = settings.get("shop_name") or "MOTOR SPARES MANAGEMENT"
    address = settings.get("address") or ""
    phone = settings.get("phone") or ""

    lines.append(center(shop_name.upper()))
    if address:
        lines.append(center(address))
    if phone:
        lines.append(center(f"Tel: {phone}"))
    lines.append(divider("="))

    # Receipt Info
    lines.append(key_val("Receipt #:", receipt_number))
    lines.append(key_val("Date:", date_str))
    lines.append(key_val("Cashier:", cashier_name))
    lines.append(key_val("Customer:", customer_name))
    lines.append(divider("-"))

    # Items Header
    if w >= 48:
        lines.append(f"{'ITEM / CODE':<28}{'QTY':>5}{'PRICE':>7}{'TOTAL':>8}")
    else:
        lines.append(f"{'ITEM':<16}{'QTY':>4}{'PRICE':>6}{'TOTAL':>6}")
    lines.append(divider("-"))

    # Line Items (Supermarket multi-line format)
    for it in items:
        p_num = getattr(it, "part_number", it.get("part_number", "")) if isinstance(it, dict) else it.part_number
        p_name = getattr(it, "part_name", it.get("part_name", "")) if isinstance(it, dict) else it.part_name
        qty = getattr(it, "quantity", it.get("quantity", 1)) if isinstance(it, dict) else it.quantity
        price = getattr(it, "unit_price", it.get("unit_price", 0.0)) if isinstance(it, dict) else it.unit_price
        subtotal = getattr(it, "subtotal", qty * price) if hasattr(it, "subtotal") else (it.get("subtotal", qty * price) if isinstance(it, dict) else qty * price)

        display_desc = f"{p_num} {p_name}".strip()
        price_str = f"${price:.2f}"
        sub_str = f"${subtotal:.2f}"
        qty_str = str(qty)

        if w >= 48:
            if len(display_desc) <= 27:
                lines.append(f"{display_desc:<28}{qty_str:>5}{price_str:>7}{sub_str:>8}")
            else:
                lines.append(display_desc)
                lines.append(f"{' ' * 20} x{qty_str:<4}{price_str:>11}{sub_str:>11}")
        else:
            lines.append(display_desc)
            lines.append(f"  {qty_str} x {price_str:<8}{sub_str:>12}")

    lines.append(divider("-"))

    # Totals
    total_str = f"${total_amount:.2f}"
    lines.append(key_val("TOTAL AMOUNT:", total_str))
    lines.append(key_val("PAYMENT METHOD:", payment_method))
    lines.append(divider("="))

    # Footer
    footer_text = settings.get("receipt_footer") or "Thank you for your business!"
    for fline in footer_text.split("\n"):
        if fline.strip():
            lines.append(center(fline.strip()))

    wa_msg = settings.get("whatsapp_message", "").strip()
    if wa_msg:
        lines.append(divider("-"))
        # Word-wrap to width
        words = wa_msg.split()
        cur_line = ""
        for word in words:
            if len(cur_line) + len(word) + 1 <= w:
                cur_line = (cur_line + " " + word).strip()
            else:
                lines.append(center(cur_line))
                cur_line = word
        if cur_line:
            lines.append(center(cur_line))

    lines.append(divider("-"))
    lines.append(center("Goods once sold cannot be refunded"))
    lines.append(center("without this receipt."))
    lines.append(center("Powered by IrrefutableAccord"))

    return "\n".join(lines) + "\n"


def build_escpos_bytes(
    settings: dict,
    receipt_number: str,
    date_str: str,
    cashier_name: str,
    customer_name: str,
    items: list,
    total_amount: float,
    payment_method: str,
    paper_width_mm: str = "80",
    cut_paper: bool = True
) -> bytes:
    """
    Constructs raw binary ESC/POS byte stream for thermal receipt printers.
    Includes hardware formatting: centered bold header, clear dividers,
    double-height totals, and paper cutter sequence.
    """
    width_chars = 48 if paper_width_mm == "80" else 32
    w = width_chars

    def divider_b(char="-"):
        return (char * w).encode("ascii", errors="replace") + b"\n"

    def key_val_b(k, v):
        space = w - len(k) - len(v)
        if space < 1:
            line = f"{k} {v}"[:w]
        else:
            line = f"{k}{' ' * space}{v}"
        return line.encode("ascii", errors="replace") + b"\n"

    b = bytearray()
    b.extend(CMD_INIT)

    # Header: Store name in Bold + Double Size
    shop_name = (settings.get("shop_name") or "MOTOR SPARES MANAGEMENT").strip()
    address = (settings.get("address") or "").strip()
    phone = (settings.get("phone") or "").strip()

    b.extend(CMD_ALIGN_CENTER)
    b.extend(CMD_BOLD_ON)
    b.extend(CMD_DOUBLE_SIZE)
    b.extend(shop_name.encode("ascii", errors="replace") + b"\n")
    b.extend(CMD_NORMAL_SIZE)
    b.extend(CMD_BOLD_OFF)

    if address:
        b.extend(address.encode("ascii", errors="replace") + b"\n")
    if phone:
        b.extend(f"Tel: {phone}".encode("ascii", errors="replace") + b"\n")

    b.extend(CMD_ALIGN_LEFT)
    b.extend(divider_b("="))

    # Receipt Metadata
    b.extend(key_val_b("Receipt #:", receipt_number))
    b.extend(key_val_b("Date:", date_str))
    b.extend(key_val_b("Cashier:", cashier_name))
    b.extend(key_val_b("Customer:", customer_name))
    b.extend(divider_b("-"))

    # Items Header
    b.extend(CMD_BOLD_ON)
    if w >= 48:
        b.extend(f"{'ITEM / CODE':<28}{'QTY':>5}{'PRICE':>7}{'TOTAL':>8}\n".encode("ascii", errors="replace"))
    else:
        b.extend(f"{'ITEM':<16}{'QTY':>4}{'PRICE':>6}{'TOTAL':>6}\n".encode("ascii", errors="replace"))
    b.extend(CMD_BOLD_OFF)
    b.extend(divider_b("-"))

    # Line Items
    for it in items:
        p_num = getattr(it, "part_number", it.get("part_number", "")) if isinstance(it, dict) else it.part_number
        p_name = getattr(it, "part_name", it.get("part_name", "")) if isinstance(it, dict) else it.part_name
        qty = getattr(it, "quantity", it.get("quantity", 1)) if isinstance(it, dict) else it.quantity
        price = getattr(it, "unit_price", it.get("unit_price", 0.0)) if isinstance(it, dict) else it.unit_price
        subtotal = getattr(it, "subtotal", qty * price) if hasattr(it, "subtotal") else (it.get("subtotal", qty * price) if isinstance(it, dict) else qty * price)

        display_desc = f"{p_num} {p_name}".strip()
        price_str = f"${price:.2f}"
        sub_str = f"${subtotal:.2f}"
        qty_str = str(qty)

        if w >= 48:
            if len(display_desc) <= 27:
                line = f"{display_desc:<28}{qty_str:>5}{price_str:>7}{sub_str:>8}\n"
                b.extend(line.encode("ascii", errors="replace"))
            else:
                b.extend((display_desc + "\n").encode("ascii", errors="replace"))
                b.extend(f"{' ' * 20} x{qty_str:<4}{price_str:>11}{sub_str:>11}\n".encode("ascii", errors="replace"))
        else:
            b.extend((display_desc + "\n").encode("ascii", errors="replace"))
            b.extend(f"  {qty_str} x {price_str:<8}{sub_str:>12}\n".encode("ascii", errors="replace"))

    b.extend(divider_b("-"))

    # Total Amount in BOLD + Double Height
    total_str = f"${total_amount:.2f}"
    b.extend(CMD_BOLD_ON)
    b.extend(CMD_DOUBLE_HEIGHT)
    b.extend(key_val_b("TOTAL AMOUNT:", total_str))
    b.extend(CMD_NORMAL_SIZE)
    b.extend(CMD_BOLD_OFF)

    b.extend(key_val_b("PAYMENT METHOD:", payment_method))
    b.extend(divider_b("="))

    # Footer
    b.extend(CMD_ALIGN_CENTER)
    footer_text = settings.get("receipt_footer") or "Thank you for your business!"
    for fline in footer_text.split("\n"):
        if fline.strip():
            b.extend(fline.strip().encode("ascii", errors="replace") + b"\n")

    wa_msg = settings.get("whatsapp_message", "").strip()
    if wa_msg:
        b.extend(divider_b("-"))
        words = wa_msg.split()
        cur_line = ""
        for word in words:
            if len(cur_line) + len(word) + 1 <= w:
                cur_line = (cur_line + " " + word).strip()
            else:
                b.extend(cur_line.encode("ascii", errors="replace") + b"\n")
                cur_line = word
        if cur_line:
            b.extend(cur_line.encode("ascii", errors="replace") + b"\n")

    b.extend(divider_b("-"))
    b.extend(b"Goods once sold cannot be refunded\n")
    b.extend(b"without this receipt.\n")
    b.extend(b"Powered by IrrefutableAccord\n")

    # Paper Feed & Cut
    if cut_paper:
        b.extend(CMD_FEED_CUT)
    else:
        b.extend(b"\n\n\n\n")

    return bytes(b)


def print_thermal_receipt(
    sale: Sale,
    receipt_number: str,
    cashier_name: str,
    customer_name: str = "Walk-in"
) -> Tuple[bool, str]:
    """
    Builds and prints a thermal supermarket-style receipt for a completed sale.
    Also saves a text copy into the receipts directory.
    Returns (success, message).
    """
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    settings = get_all_settings()

    printer_name = settings.get("thermal_printer_name", "").strip()
    paper_width = settings.get("thermal_paper_width", "80")
    cut_paper = settings.get("thermal_cut_paper", "1") == "1"

    # Date format
    try:
        dt = datetime.fromisoformat(sale.timestamp)
        date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Save text backup copy
    width_chars = 48 if paper_width == "80" else 32
    text_content = _format_supermarket_text(
        settings=settings,
        receipt_number=receipt_number,
        date_str=date_str,
        cashier_name=cashier_name,
        customer_name=customer_name,
        items=sale.items,
        total_amount=sale.total_amount,
        payment_method=sale.payment_method,
        width_chars=width_chars
    )

    txt_filename = f"{receipt_number}_thermal.txt"
    txt_path = os.path.join(RECEIPTS_DIR, txt_filename)
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_content)
    except Exception as e:
        logging.warning(f"Failed to save text receipt backup: {e}")

    # 2. Check if printer is selected
    if not printer_name:
        return False, f"Receipt saved to '{txt_filename}'. No thermal printer selected in Settings."

    # 3. Build ESC/POS bytes and send to printer
    raw_bytes = build_escpos_bytes(
        settings=settings,
        receipt_number=receipt_number,
        date_str=date_str,
        cashier_name=cashier_name,
        customer_name=customer_name,
        items=sale.items,
        total_amount=sale.total_amount,
        payment_method=sale.payment_method,
        paper_width_mm=paper_width,
        cut_paper=cut_paper
    )

    success, msg = _send_raw_to_printer(printer_name, raw_bytes, doc_name=f"Receipt {receipt_number}")
    return success, msg


def test_print_thermal_receipt(printer_name: str, paper_width: str = "80") -> Tuple[bool, str]:
    """
    Sends a sample supermarket test receipt to the specified thermal printer.
    Tests alignment, bold text, item list, totals, and paper cutting.
    """
    if not printer_name:
        return False, "Please select a printer first."

    settings = get_all_settings()

    test_items = [
        {"part_number": "AC3032", "part_name": "ACC CABLE TOY AC3032", "quantity": 2, "unit_price": 15.00, "subtotal": 30.00},
        {"part_number": "RH7001", "part_name": "AIR CLEANER HOSE Y-SER", "quantity": 1, "unit_price": 20.00, "subtotal": 20.00},
    ]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    raw_bytes = build_escpos_bytes(
        settings=settings,
        receipt_number="TEST-PRINT-001",
        date_str=now_str,
        cashier_name="Test Cashier",
        customer_name="Walk-in Customer",
        items=test_items,
        total_amount=50.00,
        payment_method="Cash",
        paper_width_mm=paper_width,
        cut_paper=True
    )

def print_credit_thermal_receipt(
    credit_order_id: int,
    customer_name: str,
    items: list,
    total_amount: float,
    cashier_name: str
) -> Tuple[bool, str]:
    """Prints a thermal receipt/docket for a Pay Later (Credit) order."""
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    settings = get_all_settings()

    printer_name = settings.get("thermal_printer_name", "").strip()
    paper_width = settings.get("thermal_paper_width", "80")
    cut_paper = settings.get("thermal_cut_paper", "1") == "1"

    receipt_number = f"CREDIT-{credit_order_id:04d}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save text copy
    width_chars = 48 if paper_width == "80" else 32
    text_content = _format_supermarket_text(
        settings=settings,
        receipt_number=receipt_number,
        date_str=now_str,
        cashier_name=cashier_name,
        customer_name=customer_name,
        items=items,
        total_amount=total_amount,
        payment_method="Pay Later (Credit) - PENDING",
        width_chars=width_chars
    )

    txt_filename = f"{receipt_number}_thermal.txt"
    txt_path = os.path.join(RECEIPTS_DIR, txt_filename)
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_content)
    except Exception as e:
        logging.warning(f"Failed to save text credit receipt backup: {e}")

    if not printer_name:
        return False, f"Credit receipt saved to '{txt_filename}'. No thermal printer configured."

    raw_bytes = build_escpos_bytes(
        settings=settings,
        receipt_number=receipt_number,
        date_str=now_str,
        cashier_name=cashier_name,
        customer_name=customer_name,
        items=items,
        total_amount=total_amount,
        payment_method="Pay Later (Credit)",
        paper_width_mm=paper_width,
        cut_paper=cut_paper
    )

    return _send_raw_to_printer(printer_name, raw_bytes, doc_name=f"Credit Order {receipt_number}")
