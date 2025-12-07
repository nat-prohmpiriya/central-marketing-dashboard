"""Currency utility functions."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("utils.currency")

# Default currency for the application
DEFAULT_CURRENCY = "THB"

# Static exchange rates (fallback when API unavailable)
# In production, use a real-time API or database
STATIC_EXCHANGE_RATES = {
    # To THB
    ("USD", "THB"): Decimal("35.00"),
    ("EUR", "THB"): Decimal("38.00"),
    ("GBP", "THB"): Decimal("44.00"),
    ("JPY", "THB"): Decimal("0.24"),
    ("CNY", "THB"): Decimal("4.90"),
    ("SGD", "THB"): Decimal("26.00"),
    ("MYR", "THB"): Decimal("7.50"),
    ("IDR", "THB"): Decimal("0.0022"),
    ("VND", "THB"): Decimal("0.0014"),
    ("PHP", "THB"): Decimal("0.63"),
    # From THB
    ("THB", "USD"): Decimal("0.0286"),
    ("THB", "EUR"): Decimal("0.0263"),
    # Same currency
    ("THB", "THB"): Decimal("1.0"),
    ("USD", "USD"): Decimal("1.0"),
}


def to_decimal(value: Any) -> Decimal:
    """Convert value to Decimal.

    Args:
        value: Value to convert (str, int, float, Decimal).

    Returns:
        Decimal value.

    Raises:
        ValueError: If value cannot be converted.
    """
    if value is None:
        return Decimal("0")

    if isinstance(value, Decimal):
        return value

    if isinstance(value, str):
        # Remove commas and whitespace
        value = value.replace(",", "").strip()
        if not value:
            return Decimal("0")

    try:
        return Decimal(str(value))
    except Exception as e:
        raise ValueError(f"Cannot convert {value} to Decimal: {e}")


def round_currency(
    amount: Decimal | float,
    decimals: int = 2,
) -> Decimal:
    """Round currency amount.

    Args:
        amount: Amount to round.
        decimals: Number of decimal places.

    Returns:
        Rounded Decimal.
    """
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    quantize_str = "0." + "0" * decimals
    return amount.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)


def get_exchange_rate(
    from_currency: str,
    to_currency: str,
) -> Decimal:
    """Get exchange rate between two currencies.

    Args:
        from_currency: Source currency code.
        to_currency: Target currency code.

    Returns:
        Exchange rate.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return Decimal("1.0")

    # Try direct rate
    key = (from_currency, to_currency)
    if key in STATIC_EXCHANGE_RATES:
        return STATIC_EXCHANGE_RATES[key]

    # Try reverse rate
    reverse_key = (to_currency, from_currency)
    if reverse_key in STATIC_EXCHANGE_RATES:
        return Decimal("1.0") / STATIC_EXCHANGE_RATES[reverse_key]

    # Try via THB
    if from_currency != "THB" and to_currency != "THB":
        to_thb = STATIC_EXCHANGE_RATES.get((from_currency, "THB"))
        from_thb = STATIC_EXCHANGE_RATES.get(("THB", to_currency))

        if to_thb and from_thb:
            return to_thb * from_thb

    logger.warning(
        "Exchange rate not found, using 1.0",
        from_currency=from_currency,
        to_currency=to_currency,
    )
    return Decimal("1.0")


def convert_currency(
    amount: Decimal | float | int | str,
    from_currency: str,
    to_currency: str = DEFAULT_CURRENCY,
    round_result: bool = True,
) -> Decimal:
    """Convert amount between currencies.

    Args:
        amount: Amount to convert.
        from_currency: Source currency code.
        to_currency: Target currency code.
        round_result: Whether to round the result.

    Returns:
        Converted amount.
    """
    amount_decimal = to_decimal(amount)

    if amount_decimal == Decimal("0"):
        return Decimal("0")

    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        if round_result:
            return round_currency(amount_decimal)
        return amount_decimal

    rate = get_exchange_rate(from_currency, to_currency)
    result = amount_decimal * rate

    if round_result:
        return round_currency(result)
    return result


def format_currency(
    amount: Decimal | float | int,
    currency: str = DEFAULT_CURRENCY,
    include_symbol: bool = True,
    locale: str = "th_TH",
) -> str:
    """Format amount as currency string.

    Args:
        amount: Amount to format.
        currency: Currency code.
        include_symbol: Include currency symbol.
        locale: Locale for formatting.

    Returns:
        Formatted currency string.
    """
    amount_decimal = to_decimal(amount)
    amount_rounded = round_currency(amount_decimal)

    # Currency symbols
    symbols = {
        "THB": "฿",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CNY": "¥",
    }

    # Format number with thousand separators
    formatted = f"{amount_rounded:,.2f}"

    if include_symbol:
        symbol = symbols.get(currency.upper(), currency)
        if currency.upper() in ("USD", "EUR", "GBP"):
            return f"{symbol}{formatted}"
        return f"{formatted} {symbol}"

    return formatted


def parse_currency_string(
    value: str,
    expected_currency: str | None = None,
) -> tuple[Decimal, str]:
    """Parse a currency string into amount and currency code.

    Args:
        value: Currency string (e.g., "$100.00", "฿500", "100 THB").
        expected_currency: Expected currency if not in string.

    Returns:
        Tuple of (amount, currency_code).
    """
    value = value.strip()

    # Symbol to currency mapping
    symbol_map = {
        "฿": "THB",
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
    }

    # Check for symbol prefix
    for symbol, currency in symbol_map.items():
        if value.startswith(symbol):
            amount_str = value[len(symbol):].strip().replace(",", "")
            return to_decimal(amount_str), currency

    # Check for currency suffix
    parts = value.split()
    if len(parts) == 2:
        amount_str, currency = parts
        return to_decimal(amount_str.replace(",", "")), currency.upper()

    # No currency found, use expected or default
    amount_str = value.replace(",", "")
    currency = expected_currency or DEFAULT_CURRENCY
    return to_decimal(amount_str), currency


def calculate_percentage(
    part: Decimal | float | int,
    whole: Decimal | float | int,
    decimals: int = 2,
) -> Decimal:
    """Calculate percentage.

    Args:
        part: Part value.
        whole: Whole value.
        decimals: Number of decimal places.

    Returns:
        Percentage as Decimal.
    """
    part_decimal = to_decimal(part)
    whole_decimal = to_decimal(whole)

    if whole_decimal == Decimal("0"):
        return Decimal("0")

    percentage = (part_decimal / whole_decimal) * Decimal("100")
    return round_currency(percentage, decimals)


def calculate_change(
    current: Decimal | float | int,
    previous: Decimal | float | int,
    as_percentage: bool = True,
) -> Decimal:
    """Calculate change between two values.

    Args:
        current: Current value.
        previous: Previous value.
        as_percentage: Return as percentage (default) or absolute.

    Returns:
        Change value.
    """
    current_decimal = to_decimal(current)
    previous_decimal = to_decimal(previous)

    absolute_change = current_decimal - previous_decimal

    if not as_percentage:
        return round_currency(absolute_change)

    if previous_decimal == Decimal("0"):
        if current_decimal > Decimal("0"):
            return Decimal("100.00")
        return Decimal("0")

    percentage_change = (absolute_change / previous_decimal) * Decimal("100")
    return round_currency(percentage_change)
