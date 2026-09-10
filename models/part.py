from dataclasses import dataclass, field
from typing import Optional

# Allowed vehicle type values — the POS and Inventory screens use these
# to filter and badge parts so a motorbike shop can find bike parts quickly.
VEHICLE_TYPES = ("Car", "Motorbike", "Both")

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
    # vehicle_type: one of 'Car', 'Motorbike', 'Both'.
    # Defaults to 'Car' so all pre-existing parts are unaffected by the migration.
    vehicle_type: str = "Car"

    def is_low_stock(self) -> bool:
        """Returns True if quantity is at or below the reorder level."""
        return self.quantity_on_hand <= self.reorder_level
