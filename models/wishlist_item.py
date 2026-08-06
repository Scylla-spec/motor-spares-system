from dataclasses import dataclass
from typing import Optional

PRIORITY_LEVELS = ["High", "Medium", "Low"]


@dataclass
class WishlistItem:
    """Data model representing a manually-added reorder wishlist entry
    (FR-21) — for parts that are unavailable/not yet catalogued, so they
    don't fall through the cracks between supplier visits.
    """
    wishlist_id: Optional[int]
    description: str
    preferred_supplier_id: Optional[int]
    priority: str  # one of PRIORITY_LEVELS
    notes: str
    date_added: str
    added_by: Optional[int]
