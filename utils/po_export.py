import os
import logging
from datetime import datetime
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from managers.settings_manager import get_all_settings
from models.purchase_order import PurchaseOrder

PO_EXPORTS_DIR = "exports"


def generate_po_pdf(po: PurchaseOrder) -> str:
    """
    Generates an official, branded Purchase Order PDF document.
    
    Returns the absolute path to the generated PDF, or empty string on failure.
    """
    os.makedirs(PO_EXPORTS_DIR, exist_ok=True)
    po_num_clean = (po.po_number or f"PO-{po.po_id}").replace("/", "-")
    timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"Purchase_Order_{po_num_clean}_{timestamp_str}.pdf"
    filepath = os.path.join(PO_EXPORTS_DIR, filename)

    settings = get_all_settings()

    try:
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter

        # --- Shop Header ---
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2.0, height - 50, settings.get("shop_name") or "Motor Spares Management")

        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2.0, height - 66, settings.get("address") or "Bulawayo, Zimbabwe")

        if settings.get("phone"):
            c.drawCentredString(width / 2.0, height - 79, f"Phone: {settings.get('phone')}")

        # --- Title Banner ---
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2.0, height - 105, "OFFICIAL PURCHASE ORDER")

        # --- PO Meta Info Box ---
        y = height - 135
        c.setLineWidth(0.5)
        c.rect(45, y - 55, 522, 60, fill=0)

        c.setFont("Helvetica-Bold", 10)
        c.drawString(55, y - 15, f"PO Number:")
        c.setFont("Helvetica", 10)
        c.drawString(135, y - 15, str(po.po_number or f"PO-#{po.po_id}"))

        c.setFont("Helvetica-Bold", 10)
        c.drawString(55, y - 32, f"Order Date:")
        c.setFont("Helvetica", 10)
        c.drawString(135, y - 32, str(po.order_date or datetime.now().strftime("%Y-%m-%d")))

        c.setFont("Helvetica-Bold", 10)
        c.drawString(55, y - 48, f"Order Status:")
        c.setFont("Helvetica", 10)
        c.drawString(135, y - 48, str(po.status).upper())

        # Supplier details right side
        c.setFont("Helvetica-Bold", 10)
        c.drawString(330, y - 15, f"Vendor / Supplier:")
        c.setFont("Helvetica", 10)
        c.drawString(440, y - 15, str(po.supplier_name or "—")[:22])

        c.setFont("Helvetica-Bold", 10)
        c.drawString(330, y - 32, f"Payment Terms:")
        c.setFont("Helvetica", 10)
        c.drawString(440, y - 32, "Net 30 / On Delivery")

        # --- Table Header ---
        y -= 80
        c.setFont("Helvetica-Bold", 9)
        c.drawString(45, y, "Item #")
        c.drawString(95, y, "Part Number")
        c.drawString(200, y, "Description")
        c.drawString(390, y, "Qty")
        c.drawString(440, y, "Unit Cost")
        c.drawString(510, y, "Subtotal")
        c.line(45, y - 4, 567, y - 4)

        # --- Table Rows ---
        y -= 18
        c.setFont("Helvetica", 9)
        items = getattr(po, "items", []) or []

        if items:
            for idx, item in enumerate(items, 1):
                if y < 90:
                    c.showPage()
                    y = height - 60
                    c.setFont("Helvetica", 9)

                subtotal = item.quantity_ordered * item.unit_cost
                c.drawString(45, y, str(idx))
                c.drawString(95, y, str(item.part_number)[:16])
                c.drawString(200, y, str(item.part_name)[:32])
                c.drawString(390, y, str(item.quantity_ordered))
                c.drawString(440, y, f"${item.unit_cost:.2f}")
                c.drawString(510, y, f"${subtotal:.2f}")
                y -= 16
        else:
            # Single lump-sum estimate fallback
            c.drawString(45, y, "1")
            c.drawString(95, y, "GENERAL")
            c.drawString(200, y, "Procurement Lot / Estimate")
            c.drawString(390, y, "1")
            c.drawString(440, y, f"${po.total_cost:.2f}")
            c.drawString(510, y, f"${po.total_cost:.2f}")
            y -= 16

        c.line(45, y - 2, 567, y - 2)

        # --- Total Cost ---
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(490, y, "TOTAL ORDER AMOUNT:")
        c.drawRightString(567, y, f"${po.total_cost:.2f}")

        # --- Signatures & Footer ---
        y -= 45
        c.setFont("Helvetica", 9)
        c.drawString(45, y, "Authorized By: ___________________________")
        c.drawString(340, y, "Supplier Acceptance: ___________________________")

        y -= 30
        c.setFont("Helvetica-Oblique", 8)
        footer_text = settings.get("receipt_footer") or "Thank you for partnering with us!"
        c.drawCentredString(width / 2.0, 35, footer_text)

        c.save()
        logging.info(f"Purchase order PDF generated at {filepath}")
        return os.path.abspath(filepath)

    except Exception as e:
        logging.error(f"Failed to generate purchase order PDF: {e}")
        return ""
