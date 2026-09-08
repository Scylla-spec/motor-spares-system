"""
Multi-Currency & Exchange Rate Engine for Motor Spares System.
Handles real-time conversion between base currency (USD) and common retail tender
currencies (Zimbabwe Gold - ZiG, South African Rand - ZAR), including tender change calculation.
"""

from typing import Dict, Tuple
from managers.settings_manager import get_all_settings


def get_exchange_rates() -> Dict[str, float]:
    """Returns current exchange rates (Units per 1 USD) from settings."""
    settings = get_all_settings()
    try:
        zig_rate = float(settings.get("rate_zig", "26.50"))
        if zig_rate <= 0:
            zig_rate = 26.50
    except (ValueError, TypeError):
        zig_rate = 26.50

    try:
        zar_rate = float(settings.get("rate_zar", "18.20"))
        if zar_rate <= 0:
            zar_rate = 18.20
    except (ValueError, TypeError):
        zar_rate = 18.20

    return {
        "USD": 1.0,
        "ZIG": zig_rate,
        "ZAR": zar_rate,
    }


def convert_usd(amount_usd: float, target_currency: str) -> float:
    """Converts a USD amount to target currency (USD, ZIG, ZAR)."""
    rates = get_exchange_rates()
    rate = rates.get(target_currency.upper(), 1.0)
    return round(amount_usd * rate, 2)


def convert_to_usd(amount: float, source_currency: str) -> float:
    """Converts an amount in source currency (USD, ZIG, ZAR) to base USD."""
    rates = get_exchange_rates()
    rate = rates.get(source_currency.upper(), 1.0)
    if rate <= 0:
        return amount
    return round(amount / rate, 2)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Formats an amount with its currency symbol/code."""
    cur = currency.upper().strip()
    if cur == "USD":
        return f"${amount:,.2f}"
    elif cur == "ZIG":
        return f"{amount:,.2f} ZiG"
    elif cur == "ZAR":
        return f"R {amount:,.2f}"
    return f"{amount:,.2f} {cur}"


def get_all_currency_equivalents(amount_usd: float) -> Dict[str, str]:
    """
    Returns a dictionary of formatted equivalent amounts in USD, ZiG, and ZAR.
    Useful for displaying live multi-currency chips under cart totals.
    """
    rates = get_exchange_rates()
    zig_val = round(amount_usd * rates["ZIG"], 2)
    zar_val = round(amount_usd * rates["ZAR"], 2)

    return {
        "USD": f"${amount_usd:,.2f}",
        "ZIG": f"{zig_val:,.2f} ZiG",
        "ZAR": f"R {zar_val:,.2f}",
        "rates_summary": f"1 USD = {rates['ZIG']:.2f} ZiG | 1 USD = {rates['ZAR']:.2f} ZAR"
    }


def calculate_tender_change(
    total_usd: float,
    tendered_amount: float,
    tender_currency: str = "USD"
) -> Dict[str, float]:
    """
    Calculates change when a customer tenders payment in any supported currency.
    Returns:
        {
            'is_sufficient': bool,
            'tendered_usd': float,
            'change_usd': float,
            'change_in_tender_currency': float,
            'shortage_in_tender_currency': float
        }
    """
    cur = tender_currency.upper().strip()
    rates = get_exchange_rates()
    rate = rates.get(cur, 1.0)

    # Convert tendered amount into USD equivalent
    tendered_usd = round(tendered_amount / rate, 2) if rate > 0 else tendered_amount

    diff_usd = round(tendered_usd - total_usd, 2)

    if diff_usd >= 0:
        change_usd = diff_usd
        change_tender_cur = round(change_usd * rate, 2)
        return {
            "is_sufficient": True,
            "tendered_usd": tendered_usd,
            "change_usd": change_usd,
            "change_in_tender_currency": change_tender_cur,
            "shortage_in_tender_currency": 0.0
        }
    else:
        shortage_usd = abs(diff_usd)
        shortage_tender_cur = round(shortage_usd * rate, 2)
        return {
            "is_sufficient": False,
            "tendered_usd": tendered_usd,
            "change_usd": 0.0,
            "change_in_tender_currency": 0.0,
            "shortage_in_tender_currency": shortage_tender_cur
        }
