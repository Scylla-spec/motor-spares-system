"""
Centralised validation rules (Section 3.5 of the project documentation).

Each function returns (is_valid: bool, error_message: str). error_message is
empty when is_valid is True. UI dialogs should call these instead of
scattering their own ad hoc checks, so the rules stay consistent everywhere
a given field is entered.
"""

MIN_PASSWORD_LENGTH = 6


def validate_part(part_number: str, name: str, cost_price: float, selling_price: float) -> tuple[bool, str]:
    """Validates a part before it is saved (add or edit)."""
    if not part_number or not part_number.strip():
        return False, "Part number is required."
    if not name or not name.strip():
        return False, "Part name is required."
    if cost_price < 0:
        return False, "Cost price cannot be negative."
    if selling_price <= 0:
        return False, "Selling price must be greater than 0."
    if selling_price < cost_price:
        return False, "Selling price must be greater than or equal to cost price."
    return True, ""


def validate_required_name(name: str, field_label: str = "Name") -> tuple[bool, str]:
    """Validates a required name field (Customer, Supplier)."""
    if not name or not name.strip():
        return False, f"{field_label} is required."
    return True, ""


def validate_new_user(username: str, password: str) -> tuple[bool, str]:
    """Validates a new user account before creation."""
    if not username or not username.strip():
        return False, "Username is required."
    if not password:
        return False, "Password is required."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    return True, ""


def validate_quantity(quantity: int) -> tuple[bool, str]:
    """Validates a quantity used in a sale or stock-in (must be > 0)."""
    if quantity <= 0:
        return False, "Quantity must be greater than 0."
    return True, ""