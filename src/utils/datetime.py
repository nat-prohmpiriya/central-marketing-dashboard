"""Datetime utility functions."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Common timezones
TZ_UTC = ZoneInfo("UTC")
TZ_BANGKOK = ZoneInfo("Asia/Bangkok")

# Default timezone for the application
DEFAULT_TIMEZONE = TZ_BANGKOK


def now_utc() -> datetime:
    """Get current UTC datetime (timezone-aware).

    Returns:
        Current datetime in UTC.
    """
    return datetime.now(timezone.utc)


def now_local(tz: ZoneInfo = DEFAULT_TIMEZONE) -> datetime:
    """Get current datetime in local timezone.

    Args:
        tz: Target timezone. Defaults to Bangkok.

    Returns:
        Current datetime in specified timezone.
    """
    return datetime.now(tz)


def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC.

    Args:
        dt: Datetime to convert. If naive, assumes local timezone.

    Returns:
        Datetime in UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DEFAULT_TIMEZONE)
    return dt.astimezone(TZ_UTC)


def to_local(dt: datetime, tz: ZoneInfo = DEFAULT_TIMEZONE) -> datetime:
    """Convert datetime to local timezone.

    Args:
        dt: Datetime to convert. If naive, assumes UTC.
        tz: Target timezone. Defaults to Bangkok.

    Returns:
        Datetime in local timezone.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_UTC)
    return dt.astimezone(tz)


def from_timestamp(ts: int | float, tz: ZoneInfo = TZ_UTC) -> datetime:
    """Convert Unix timestamp to datetime.

    Args:
        ts: Unix timestamp (seconds since epoch).
        tz: Target timezone for the result.

    Returns:
        Datetime object.
    """
    return datetime.fromtimestamp(ts, tz=tz)


def to_timestamp(dt: datetime) -> int:
    """Convert datetime to Unix timestamp.

    Args:
        dt: Datetime to convert.

    Returns:
        Unix timestamp as integer.
    """
    return int(dt.timestamp())


def parse_iso(iso_string: str) -> datetime:
    """Parse ISO format datetime string.

    Handles various formats:
    - 2024-01-15T10:30:00Z
    - 2024-01-15T10:30:00+07:00
    - 2024-01-15T10:30:00

    Args:
        iso_string: ISO format datetime string.

    Returns:
        Parsed datetime object (timezone-aware).
    """
    # Handle 'Z' suffix
    if iso_string.endswith("Z"):
        iso_string = iso_string[:-1] + "+00:00"

    dt = datetime.fromisoformat(iso_string)

    # If naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_UTC)

    return dt


def format_iso(dt: datetime) -> str:
    """Format datetime as ISO string.

    Args:
        dt: Datetime to format.

    Returns:
        ISO format string with timezone.
    """
    return dt.isoformat()


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """Format datetime as date string.

    Args:
        dt: Datetime to format.
        fmt: strftime format string.

    Returns:
        Formatted date string.
    """
    return dt.strftime(fmt)


def start_of_day(dt: datetime | None = None, tz: ZoneInfo = DEFAULT_TIMEZONE) -> datetime:
    """Get start of day (midnight) for a date.

    Args:
        dt: Date to get start of. Defaults to today.
        tz: Timezone for the calculation.

    Returns:
        Datetime at midnight.
    """
    if dt is None:
        dt = now_local(tz)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime | None = None, tz: ZoneInfo = DEFAULT_TIMEZONE) -> datetime:
    """Get end of day (23:59:59.999999) for a date.

    Args:
        dt: Date to get end of. Defaults to today.
        tz: Timezone for the calculation.

    Returns:
        Datetime at end of day.
    """
    if dt is None:
        dt = now_local(tz)
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def date_range(
    start_date: datetime,
    end_date: datetime,
    step: timedelta = timedelta(days=1),
) -> list[datetime]:
    """Generate a list of dates between start and end.

    Args:
        start_date: Start of range (inclusive).
        end_date: End of range (inclusive).
        step: Step between dates.

    Returns:
        List of datetime objects.
    """
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += step
    return dates


def days_ago(days: int, tz: ZoneInfo = DEFAULT_TIMEZONE) -> datetime:
    """Get datetime N days ago.

    Args:
        days: Number of days ago.
        tz: Timezone for the calculation.

    Returns:
        Datetime N days ago at midnight.
    """
    dt = now_local(tz) - timedelta(days=days)
    return start_of_day(dt, tz)


def get_date_range_for_period(
    period: str,
    tz: ZoneInfo = DEFAULT_TIMEZONE,
) -> tuple[datetime, datetime]:
    """Get date range for a named period.

    Args:
        period: Period name ('today', 'yesterday', 'last_7_days',
                'last_30_days', 'this_month', 'last_month').
        tz: Timezone for the calculation.

    Returns:
        Tuple of (start_date, end_date).
    """
    today = start_of_day(now_local(tz), tz)

    if period == "today":
        return today, end_of_day(today, tz)

    elif period == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, end_of_day(yesterday, tz)

    elif period == "last_7_days":
        start = today - timedelta(days=6)
        return start, end_of_day(today, tz)

    elif period == "last_30_days":
        start = today - timedelta(days=29)
        return start, end_of_day(today, tz)

    elif period == "this_month":
        start = today.replace(day=1)
        return start, end_of_day(today, tz)

    elif period == "last_month":
        first_of_this_month = today.replace(day=1)
        end = first_of_this_month - timedelta(days=1)
        start = end.replace(day=1)
        return start_of_day(start, tz), end_of_day(end, tz)

    else:
        raise ValueError(f"Unknown period: {period}")
