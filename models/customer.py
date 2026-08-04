from dataclasses import dataclass
from typing import Optional
from utils.numbering import generate_customer_code


@dataclass
class Customer:
    """Data model representing a customer."""
    customer_id: Optional[int]
    name: str
    phone: str
    credit_balance: float = 0.0

    @property
    def customer_code(self) -> str:
        """Returns customer code formatted as CUS-NNNNN."""
        return generate_customer_code(self.customer_id) if self.customer_id else ""
