"""Pure, shared validation for public discovery filter values."""
from __future__ import annotations

import math


def parse_max_price(value: str | None) -> float:
    """Ignore invalid, infinite, negative or unreasonably large price filters."""
    try:
        price = float(value) if value not in (None, "") else 0.0
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(price) or price < 0 or price > 100_000_000:
        return 0.0
    return price
