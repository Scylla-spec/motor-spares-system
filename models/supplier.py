from dataclasses import dataclass
from typing import Optional

@dataclass
class Supplier:
    """Data model representing a supplier."""
    supplier_id: Optional[int]
    name: str
    contact_phone: str
    address: str
