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

    # original_unit_price: catalogue list price before any negotiation.
    # None if the price was not negotiated (i.e. it equals unit_price).
    original_unit_price: Optional[float] = None

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price

    @property
    def was_negotiated(self) -> bool:
        """True if the cashier overrode the catalogue price for this item."""
        return (
            self.original_unit_price is not None
            and abs(self.original_unit_price - self.unit_price) > 0.001
        )


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

    # Multi-currency fields (base currency is always USD)
    currency: str = "USD"          # Settlement currency chosen at checkout
    exchange_rate: float = 1.0     # Rate used: 1 USD = X currency units
    amount_paid_curr: Optional[float] = None  # Amount recorded in settlement currency
