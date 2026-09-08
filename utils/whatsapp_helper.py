"""
WhatsApp Direct Dispatch Helper for Motor Spares System.
Generates URL-encoded direct WhatsApp message links (wa.me) for instant 1-click
dispatch of payment reminders and digital sales slips via WhatsApp Web or Desktop.
Does not require paid third-party API keys or monthly subscriptions.
"""

import re
import urllib.parse
import logging
from typing import Optional, List
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from managers.settings_manager import get_all_settings


def normalize_phone_number(phone: str, default_prefix: Optional[str] = None) -> str:
    """
    Cleans and standardizes a phone number into international digit format (e.g. 263771234567).
    Strips spaces, brackets, hyphens, and leading plus.
    Replaces leading zero with default country code if provided.
    """
    if not phone:
        return ""

    if default_prefix is None:
        settings = get_all_settings()
        default_prefix = settings.get("phone_country_code", "+263").strip()

    # Clean non-digits
    prefix_clean = re.sub(r"\D", "", default_prefix) or "263"
    digits = re.sub(r"\D", "", phone)

    if not digits:
        return ""

    # If starts with single 0 (e.g. 0771234567 -> 263771234567)
    if digits.startswith("0"):
        digits = prefix_clean + digits[1:]
    # If doesn't start with prefix and is short (e.g. 771234567)
    elif len(digits) <= 9:
        digits = prefix_clean + digits

    return digits


def open_whatsapp_chat(phone: str, message: str) -> bool:
    """
    Opens WhatsApp Web or Desktop app with pre-filled message targeted to the phone number.
    Returns True if URL was successfully dispatched to desktop services.
    """
    clean_phone = normalize_phone_number(phone)
    if not clean_phone:
        logging.warning("Cannot open WhatsApp: invalid or missing phone number.")
        return False

    encoded_msg = urllib.parse.quote(message)
    wa_url = f"https://wa.me/{clean_phone}?text={encoded_msg}"

    try:
        QDesktopServices.openUrl(QUrl(wa_url))
        return True
    except Exception as e:
        logging.error(f"Failed to launch WhatsApp URL: {e}")
        import webbrowser
        try:
            webbrowser.open(wa_url)
            return True
        except Exception as e2:
            logging.error(f"Fallback browser open also failed: {e2}")
            return False


def build_credit_reminder_message(
    customer_name: str,
    credit_order_id: int,
    total_amount: float,
    due_date: Optional[str] = None
) -> str:
    """Constructs a polite, professional credit settlement reminder for WhatsApp."""
    settings = get_all_settings()
    shop_name = settings.get("shop_name", "Motor Spares Management").strip()
    phone = settings.get("phone", "").strip()

    due_str = f" due on {due_date}" if due_date else ""

    msg = (
        f"Hello {customer_name},\n\n"
        f"This is a courtesy reminder from *{shop_name}*.\n"
        f"You have an outstanding balance of *${total_amount:.2f}* for Credit Order *#{credit_order_id:04d}*{due_str}.\n\n"
        f"Kindly arrange settlement at your earliest convenience. "
        f"Thank you for choosing {shop_name}!"
    )
    if phone:
        msg += f"\n\nInquiries: {phone}"

    return msg


def build_pos_receipt_message(
    customer_name: str,
    receipt_number: str,
    items: list,
    total_amount: float,
    payment_method: str
) -> str:
    """Constructs a clean digital receipt summary to send via WhatsApp."""
    settings = get_all_settings()
    shop_name = settings.get("shop_name", "Motor Spares Management").strip()

    lines = [
        f"🧾 *OFFICIAL RECEIPT — {shop_name.upper()}*",
        f"Receipt #: *{receipt_number}*",
        f"Customer: {customer_name}",
        f"Payment: {payment_method}",
        "------------------------------------"
    ]

    for it in items:
        p_num = getattr(it, "part_number", it.get("part_number", "")) if isinstance(it, dict) else it.part_number
        p_name = getattr(it, "part_name", it.get("part_name", "")) if isinstance(it, dict) else it.part_name
        qty = getattr(it, "quantity", it.get("quantity", 1)) if isinstance(it, dict) else it.quantity
        price = getattr(it, "unit_price", it.get("unit_price", 0.0)) if isinstance(it, dict) else it.unit_price
        subtotal = getattr(it, "subtotal", qty * price) if hasattr(it, "subtotal") else (it.get("subtotal", qty * price) if isinstance(it, dict) else qty * price)
        lines.append(f"• {p_num} {p_name} | {qty}x @ ${price:.2f} = *${subtotal:.2f}*")

    lines.append("------------------------------------")
    lines.append(f"💰 *TOTAL: ${total_amount:.2f}*")
    lines.append("------------------------------------")
    footer = settings.get("receipt_footer") or "Thank you for your business!"
    lines.append(footer)

    return "\n".join(lines)
