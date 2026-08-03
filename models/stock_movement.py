from dataclasses import dataclass
from typing import Optional

@dataclass
class StockMovement:
    """Data model representing a stock movement transaction."""
    movement_id: Optional[int]
    part_id: int
    movement_type: str  # 'IN' or 'OUT'
    quantity: int
    reason: str         # e.g., 'Sale', 'Purchase', 'Adjustment', 'Damage'
    timestamp: str      # ISO format datetime string
