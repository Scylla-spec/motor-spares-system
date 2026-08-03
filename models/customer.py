from dataclasses import dataclass
from typing import Optional

@dataclass
class Customer:
    """Data model representing a customer."""
    customer_id: Optional[int]
    name: str
    phone: str
    credit_balance: float = 0.0
