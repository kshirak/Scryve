"""Date parsing helpers tolerant of the many shapes real datasets ship."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from dateutil import parser as dateutil_parser


def parse_date_value(value: Any) -> Optional[date]:
    """Coerce a heterogeneous value into a `date`.

    Handles ISO strings, `YYYY-MM`, `YYYY`, datetime instances, and date
    instances. Returns `None` for empty / unparseable values rather than
    raising; the loader logs malformed records separately.

    Args:
        value: Raw value pulled from a JSON record.

    Returns:
        A `date` instance or `None`.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        try:
            return date(int(value), 1, 1)
        except (ValueError, OverflowError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"present", "current", "now"}:
            return None
        try:
            return dateutil_parser.parse(text, default=datetime(2000, 1, 1)).date()
        except (ValueError, OverflowError, dateutil_parser.ParserError):
            return None
    return None


def parse_year(value: Any) -> Optional[int]:
    """Coerce a value into a 4-digit year.

    Args:
        value: Raw value (int, float, string, or date-like).

    Returns:
        Year as int, or `None` when the value cannot be interpreted.
    """
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value if 1900 <= value <= 2100 else None
    parsed = parse_date_value(value)
    return parsed.year if parsed else None


def duration_years(
    start: Optional[date],
    end: Optional[date],
    *,
    reference: Optional[date] = None,
) -> Optional[float]:
    """Return the inclusive duration between `start` and `end`, in years.

    When `end` is `None`, the duration is computed to `reference` (default
    today). Negative durations are clamped to 0 since they almost always
    indicate dirty input.

    Args:
        start: Start date of the period.
        end: End date, or `None` for "current".
        reference: Reference date used when `end` is `None`.

    Returns:
        Duration in years (float) or `None` when `start` is missing.
    """
    if start is None:
        return None
    end_date = end or reference or date.today()
    delta_days = (end_date - start).days
    if delta_days < 0:
        return 0.0
    return round(delta_days / 365.25, 2)
