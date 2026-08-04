from datetime import datetime


def generate_customer_code(customer_id: int) -> str:
    """
    Formats customer ID into standard CUS-NNNNN format.
    Example: 1 -> CUS-00001, 102 -> CUS-00102
    """
    if not customer_id:
        return ""
    return f"CUS-{int(customer_id):05d}"


def generate_receipt_number(cursor, sale_date: datetime = None) -> str:
    """
    Generates daily resetting receipt number REC-YYYYMMDD-NNNN.
    Counts sales for the target date to derive sequence number NNNN.
    """
    if sale_date is None:
        sale_date = datetime.now()

    date_str = sale_date.strftime("%Y%m%d")
    date_prefix = sale_date.strftime("%Y-%m-%d")

    cursor.execute(
        "SELECT COUNT(*) FROM Sale WHERE date(timestamp) = date(?)",
        (date_prefix,),
    )
    count = cursor.fetchone()[0] + 1
    return f"REC-{date_str}-{count:04d}"


def generate_po_number(cursor, order_date: datetime = None) -> str:
    """
    Generates daily resetting purchase order number PO-YYYYMMDD-NNNN.
    Counts orders for the target date to derive sequence number NNNN.
    """
    if order_date is None:
        order_date = datetime.now()

    date_str = order_date.strftime("%Y%m%d")
    date_prefix = order_date.strftime("%Y-%m-%d")

    cursor.execute(
        "SELECT COUNT(*) FROM PurchaseOrder WHERE date(order_date) = date(?)",
        (date_prefix,),
    )
    count = cursor.fetchone()[0] + 1
    return f"PO-{date_str}-{count:04d}"
