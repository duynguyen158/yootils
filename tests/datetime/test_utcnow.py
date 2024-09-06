from datetime import UTC, datetime, timedelta

from yootils.datetime.utcnow import utcnow


def test_utcnow() -> None:
    timestamp = utcnow()

    # Check timezone
    assert timestamp.tzinfo == UTC

    # Check created timestamp is close to current time
    TOLERANCE_SECONDS = 1
    assert timestamp - datetime.now(tz=UTC) < timedelta(seconds=TOLERANCE_SECONDS)
