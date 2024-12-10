from datetime import UTC, datetime


def utcdatetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
) -> datetime:
    """
    Generates a datetime object in UTC timezone.

    Args:
        year (int): Year.
        month (int): Month.
        day (int): Day.
        hour (int, optional): Hour. Defaults to 0.
        minute (int, optional): Minute. Defaults to 0.
        second (int, optional): Second. Defaults to 0.
        microsecond (int, optional): Microsecond. Defaults to 0.

    Returns:
        datetime: The datetime object in UTC.
    """
    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=UTC)
