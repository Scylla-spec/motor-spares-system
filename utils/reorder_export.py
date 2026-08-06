import os
import logging
from datetime import datetime
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from managers.settings_manager import get_all_settings

REORDER_EXPORTS_DIR = "reorder_exports"


def generate_reorder_pdf(low_stock_parts: List[Dict[str, Any]], wishlist_items: List[Dict[str, Any]] = None) -> str:
    """
    Generates a PDF listing all parts currently at or below their reorder
    level (FR-20), plus any manually-added reorder wishlist items (FR-21),
    so it can be printed or taken to a supplier.

    `low_stock_parts` is expected in the shape returned by
    managers.reports_manager.get_low_stock_parts().
    `wishlist_items` (optional) is expected in the shape returned by
    managers.wishlist_manager.get_all_wishlist_items() \u2014 already sorted
    High \u2192 Medium \u2192 Low priority.

    Returns the absolute path to the generated PDF, or "" on failure.
    """
    wishlist_items = wishlist_items or []
    os.makedirs(REORDER_EXPORTS_DIR, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"reorder-list-{timestamp_str}.pdf"
    filepath = os.path.join(REORDER_EXPORTS_DIR, filename)

    settings = get_all_settings()

    try:
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2.0, height - 50, settings.get("shop_name") or "Motor Spares Management")

        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2.0, height - 65, settings.get("address") or "")

        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(width / 2.0, height - 95, "Reorder List")

        c.setFont("Helvetica", 9)
        generated_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.drawCentredString(width / 2.0, height - 110, f"Generated: {generated_str}")

        # Table header
        y = height - 145
        c.setFont("Helvetica-Bold", 9)
        c.drawString(45, y, "Part #")
        c.drawString(140, y, "Name")
        c.drawString(300, y, "Brand")
        c.drawString(380, y, "On Hand")
        c.drawString(440, y, "Reorder Lvl")
        c.drawString(510, y, "Shortage")
        c.line(45, y - 5, 555, y - 5)

        # Rows
        y -= 20
        c.setFont("Helvetica", 9)
        for part in low_stock_parts:
            if y < 80:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 9)

            c.drawString(45, y, str(part.get("part_number", "")))
            c.drawString(140, y, str(part.get("name", ""))[:28])
            c.drawString(300, y, str(part.get("brand", ""))[:14])
            c.drawString(380, y, str(part.get("quantity_on_hand", "")))
            c.drawString(440, y, str(part.get("reorder_level", "")))
            c.drawString(510, y, str(part.get("shortage", "")))
            y -= 15

        if not low_stock_parts:
            c.setFont("Helvetica-Oblique", 10)
            c.drawString(45, y, "No parts are currently at or below their reorder level.")
            y -= 20

        # --- Reorder Wishlist section (FR-21) ---
        y -= 25
        if y < 100:
            c.showPage()
            y = height - 60

        c.setFont("Helvetica-Bold", 12)
        c.drawString(45, y, "Reorder Wishlist (unavailable / uncatalogued items)")
        y -= 20

        if wishlist_items:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(45, y, "Priority")
            c.drawString(110, y, "Description")
            c.drawString(340, y, "Preferred Supplier")
            c.drawString(470, y, "Notes")
            c.line(45, y - 5, 555, y - 5)
            y -= 20

            c.setFont("Helvetica", 9)
            for item in wishlist_items:
                if y < 80:
                    c.showPage()
                    y = height - 60
                    c.setFont("Helvetica", 9)

                c.drawString(45, y, str(item.get("priority", "")))
                c.drawString(110, y, str(item.get("description", ""))[:38])
                c.drawString(340, y, str(item.get("supplier_name") or "\u2014")[:20])
                c.drawString(470, y, str(item.get("notes") or "")[:18])
                y -= 15
        else:
            c.setFont("Helvetica-Oblique", 10)
            c.drawString(45, y, "No wishlist items.")

        c.save()
        logging.info(f"Reorder list exported to {filepath}")
        return os.path.abspath(filepath)

    except Exception as e:
        logging.error(f"Failed to generate reorder list PDF: {e}")
        return ""
