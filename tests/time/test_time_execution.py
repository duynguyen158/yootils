import time

import pytest

from yootils.time.time_execution import time_execution


def test_time_execution() -> None:
    SECONDS_TO_SLEEP = 1

    with time_execution() as timer:
        time.sleep(SECONDS_TO_SLEEP)

    assert timer.seconds == pytest.approx(SECONDS_TO_SLEEP, rel=0.01)


def test_time_execution_reuse() -> None:
    with time_execution() as timer:
        time.sleep(1)

    assert timer.seconds == pytest.approx(1, rel=0.01)

    # This is discouraged on a typing level but not prevented during runtime
    # If possible, please avoid reusing the timer instance
    with timer() as timer:  # type: ignore[misc]
        time.sleep(2)

    assert timer.seconds == pytest.approx(2, rel=0.01)
