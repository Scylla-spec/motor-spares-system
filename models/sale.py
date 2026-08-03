from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class SaleItem:
    """Data model representing a single line item in a sale."""
    sale_item_id: Optional[int]
    sale_id: Optional[int]
    part_id: int
    quantity: int
    unit_price: float
    
    # Optional fields for UI display purposes
    part_name: str = ""
    part_number: str = ""
    
    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class Sale:
    """Data model representing a completed sale transaction."""
    sale_id: Optional[int]
    total_amount: float
    payment_method: str
    timestamp: str
    cashier_id: int
    customer_id: Optional[int] = None
    items: List[SaleItem] = field(default_factory=list)
