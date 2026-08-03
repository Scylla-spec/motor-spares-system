import os
import logging
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from models.sale import Sale

RECEIPTS_DIR = "receipts"
os.makedirs(RECEIPTS_DIR, exist_ok=True)

def generate_pdf_receipt(sale: Sale, receipt_number: str, cashier_name: str, customer_name: str = "Walk-in") -> str:
    """
    Generates a PDF receipt for a sale and saves it to the receipts directory.
    Returns the absolute path to the generated PDF.
    """
    filename = f"{receipt_number}.pdf"
    filepath = os.path.join(RECEIPTS_DIR, filename)
    
    try:
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2.0, height - 50, "Motor Spares Management")
        
        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2.0, height - 65, "123 Auto Lane, Bulawayo, Zimbabwe")
        c.drawCentredString(width / 2.0, height - 80, "Tel: +263 77 123 4567")
        
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
        c.drawCentredString(width / 2.0, 50, "Thank you for your business!")
        
        c.save()
        logging.info(f"Receipt {receipt_number} generated successfully at {filepath}")
        return os.path.abspath(filepath)
        
    except Exception as e:
        logging.error(f"Failed to generate receipt {receipt_number}: {e}")
        return ""
