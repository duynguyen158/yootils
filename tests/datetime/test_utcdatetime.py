from datetime import UTC, datetime

from yootils.datetime.utcdatetime import utcdatetime


def test_utcdatetime_as_date() -> None:
    timestamp = utcdatetime(2021, 1, 1)

    # Check timezone
    assert timestamp.tzinfo == UTC

    # Check created timestamp is close to expected time
    assert timestamp == datetime(2021, 1, 1, 0, 0, 0, tzinfo=UTC)


def test_utcdatetime_as_timestamp() -> None:
    timestamp = utcdatetime(2021, 1, 1, 12, 34, 56)

    # Check timezone
    assert timestamp.tzinfo == UTC

    # Check created timestamp is close to expected time
    assert timestamp == datetime(2021, 1, 1, 12, 34, 56, tzinfo=UTC)
