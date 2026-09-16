"""Small display-formatting helpers shared by pages and plots."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def format_money(value: float, digits: int = 2, *, signed: bool = False) -> str:
    """Format currency with standard display rounding across app views."""
    quant = Decimal('1') if digits == 0 else Decimal('1').scaleb(-digits)
    amount = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    if signed:
        sign = '+' if amount >= 0 else '-'
        amount = abs(amount)
        return f'{sign}${amount:,.{digits}f}'
    return f'${amount:,.{digits}f}'
