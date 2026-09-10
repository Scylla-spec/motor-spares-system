from dataclasses import dataclass
from typing import Optional

@dataclass
class Part:
    """Data model representing a part in the inventory."""
    part_id: Optional[int]
    part_number: str
    name: str
    category: str
    brand: str
    compatible_vehicles: str
    quantity_on_hand: int
    cost_price: float
    selling_price: float
    reorder_level: int
    supplier_id: Optional[int] = None
    
    def is_low_stock(self) -> bool:
        """Returns True if quantity is at or below the reorder level."""
        return self.quantity_on_hand <= self.reorder_level
