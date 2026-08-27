from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class CreditOrderItem:
    item_id: Optional[int]
    credit_id: Optional[int]
    part_id: int
    part_number: str
    part_name: str
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class CreditOrder:
    credit_id: Optional[int]
    customer_name: str
    total_amount: float
    created_at: str
    customer_id: Optional[int] = None
    customer_phone: Optional[str] = None
    amount_paid: float = 0.0
    status: str = "Pending"  # 'Pending' or 'Paid'
    due_date: Optional[str] = None
    paid_at: Optional[str] = None
    cashier_id: Optional[int] = None
    notes: Optional[str] = None
    items: List[CreditOrderItem] = field(default_factory=list)
