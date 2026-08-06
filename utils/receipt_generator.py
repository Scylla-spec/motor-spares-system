import os
import logging
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from models.sale import Sale
from managers.settings_manager import get_all_settings

RECEIPTS_DIR = "receipts"

def generate_pdf_receipt(sale: Sale, receipt_number: str, cashier_name: str, customer_name: str = "Walk-in") -> str:
    """
    Generates a PDF receipt for a sale and saves it to the receipts directory.
    Returns the absolute path to the generated PDF.
    """
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    filename = f"{receipt_number}.pdf"
    filepath = os.path.join(RECEIPTS_DIR, filename)

    settings = get_all_settings()

    try:
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter

        # Logo (if one has been set in Settings) — drawn top-left so it
        # doesn't collide with the centred header text.
        if settings.get("logo_path") and os.path.isfile(settings["logo_path"]):
            try:
                c.drawImage(
                    settings["logo_path"], 50, height - 85,
                    width=50, height=50, preserveAspectRatio=True, mask='auto'
                )
            except Exception as img_err:
                logging.warning(f"Could not draw logo on receipt: {img_err}")

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2.0, height - 50, settings.get("shop_name") or "Motor Spares Management")

        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2.0, height - 65, settings.get("address") or "")
        c.drawCentredString(width / 2.0, height - 80, f"Tel: {settings.get('phone') or ''}")
        
        # Receipt details
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 120, f"Receipt Number: {receipt_number}")
        
        c.setFont("Helvetica", 10)
        formatted_date = datetime.fromisoformat(sale.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        c.drawString(50, height - 135, f"Date: {formatted_date}")
        c.drawString(50, height - 150, f"Cashier: {cashier_name}")
        c.drawString(50, height - 165, f"Customer: {customer_name}")
        
        # Line Items Header
        y = height - 200
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Item Description")
        c.drawString(300, y, "Qty")
        c.drawString(380, y, "Unit Price")
        c.drawString(480, y, "Total")
        c.line(50, y - 5, 550, y - 5)
        
        # Line Items
        y -= 20
        c.setFont("Helvetica", 10)
        for item in sale.items:
            # Handle long names slightly by truncating
            display_name = f"{item.part_number} - {item.part_name}"[:40] 
            
            c.drawString(50, y, display_name)
            c.drawString(300, y, str(item.quantity))
            c.drawString(380, y, f"${item.unit_price:.2f}")
            c.drawString(480, y, f"${item.subtotal:.2f}")
            y -= 15
            
            # Prevent falling off page
            if y < 100:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)
                
        # Totals
        c.line(50, y - 5, 550, y - 5)
        y -= 25
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(380, y, "Total Amount:")
        c.drawString(480, y, f"${sale.total_amount:.2f}")
        
        y -= 15
        c.setFont("Helvetica", 10)
        c.drawString(380, y, "Payment Method:")
        c.drawString(480, y, sale.payment_method)
        
        # Footer
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(width / 2.0, 50, settings.get("receipt_footer") or "Thank you for your business!")
        
        c.save()
        logging.info(f"Receipt {receipt_number} generated successfully at {filepath}")
        return os.path.abspath(filepath)
        
    except Exception as e:
        logging.error(f"Failed to generate receipt {receipt_number}: {e}")
        return ""
