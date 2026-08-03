from dataclasses import dataclass
from typing import Optional

@dataclass
class PurchaseOrder:
    """Data model representing a purchase order."""
    po_id: Optional[int]
    supplier_id: int
    status: str  # 'Draft', 'Ordered', 'Received'
    order_date: Optional[str]
    total_cost: float
    
    # Optional fields for UI display
    supplier_name: str = ""
