from datetime import UTC, datetime


def utcnow() -> datetime:
    """
    Generates a current timestamp in UTC timezone.

    Returns:
        datetime: The current timestamp in UTC.
    """
    return datetime.now(tz=UTC)
