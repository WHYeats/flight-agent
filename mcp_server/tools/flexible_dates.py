from datetime import date, timedelta


def _resolve_date(date_str: str) -> date | None:
    """
    Parse a date string in YYYY-MM-DD or MM-DD format.
    For MM-DD, picks the next upcoming occurrence relative to today.
    Returns None if the string is invalid.
    """
    date_str = date_str.strip()
    if not date_str:
        return None
    try:
        if len(date_str) <= 5:
            # MM-DD format — infer year
            today = date.today()
            candidate = date.fromisoformat(f"{today.year}-{date_str}")
            if candidate < today:
                candidate = date.fromisoformat(f"{today.year + 1}-{date_str}")
            return candidate
        return date.fromisoformat(date_str)
    except ValueError:
        return None


def expand_dates(date_from: str, date_to: str = "", buffer_days: int = 0) -> list[str]:
    """
    Expand a date or date range into a list of YYYY-MM-DD strings for flight searching.
    Accepts MM-DD or YYYY-MM-DD; year is inferred automatically for MM-DD.

    Mode 1 (range): date_from + date_to → all dates inclusive.
    Mode 2 (buffer): date_from + buffer_days → center ± buffer_days.

    Args:
        date_from:   Start/center date (MM-DD or YYYY-MM-DD).
        date_to:     End date — Mode 1 only.
        buffer_days: Days around center — Mode 2 only.

    --- Instructions for the LLM ---
    - Always call this tool when the user specifies a date, even a single exact one.
    - "around"/"roughly" → Mode 2, buffer_days=2. "early/mid/late [month]" → Mode 1.
    - Call search_flights once per date returned.
    """
    start = _resolve_date(date_from)
    if start is None:
        return []

    if date_to:
        # Mode 1: date range
        end = _resolve_date(date_to)
        if end is None:
            return []
        if end < start:
            return []
    else:
        # Mode 2: buffer around a center date
        start = start - timedelta(days=buffer_days)
        end = date.fromisoformat(date_from) + timedelta(days=buffer_days)

    result = []
    current = start
    while current <= end:
        result.append(current.isoformat())
        current += timedelta(days=1)

    return result
