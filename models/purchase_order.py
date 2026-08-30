from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class PurchaseOrderItem:
    """Data model representing a single line item on a purchase order."""
    po_item_id: Optional[int]
    po_id: Optional[int]
    part_id: int
    part_number: str
    part_name: str
    quantity_ordered: int
    unit_cost: float
    subtotal: float


@dataclass
class PurchaseOrder:
    """Data model representing a purchase order."""
    po_id: Optional[int]
    supplier_id: int
    status: str  # 'Draft', 'Ordered', 'Received'
    order_date: Optional[str]
    total_cost: float
    po_number: str = ""

    # Optional fields for UI display
    supplier_name: str = ""
    items: List[PurchaseOrderItem] = field(default_factory=list)
