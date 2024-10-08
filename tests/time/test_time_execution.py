import asyncio
import time

import pytest

from yootils.time.time_execution import time_execution, time_execution_async

TOLERANCE = 0.01


def test_time_execution() -> None:
    SECONDS_TO_SLEEP = 1

    with time_execution() as timer:
        time.sleep(SECONDS_TO_SLEEP)

    assert timer.seconds_elapsed == pytest.approx(SECONDS_TO_SLEEP, rel=TOLERANCE)


def test_time_execution_reuse() -> None:
    with time_execution() as timer:
        time.sleep(1)

    assert timer.seconds_elapsed == pytest.approx(1, rel=TOLERANCE)

    # This is discouraged on a typing level but not prevented during runtime
    # If possible, please avoid reusing the timer instance
    with timer() as timer:  # type: ignore[misc]
        time.sleep(2)

    assert timer.seconds_elapsed == pytest.approx(2, rel=TOLERANCE)


@pytest.mark.asyncio
async def test_time_execution_async() -> None:
    SECONDS_TO_SLEEP = 1

    async with time_execution_async() as timer:
        await asyncio.sleep(SECONDS_TO_SLEEP)

    assert timer.seconds_elapsed == pytest.approx(SECONDS_TO_SLEEP, rel=TOLERANCE)


@pytest.mark.asyncio
async def test_time_execution_async_reuse() -> None:
    async with time_execution_async() as timer:
        await asyncio.sleep(1)

    assert timer.seconds_elapsed == pytest.approx(1, rel=TOLERANCE)

    # This is discouraged on a typing level but not prevented during runtime
    # If possible, please avoid reusing the timer instance
    async with timer() as timer:  # type: ignore[misc]
        await asyncio.sleep(2)

    assert timer.seconds_elapsed == pytest.approx(2, rel=TOLERANCE)


@pytest.mark.asyncio
async def test_time_execution_async_multiple() -> None:
    async def sleep(seconds: float) -> float:
        async with time_execution_async() as timer:
            await asyncio.sleep(seconds)

        return timer.seconds_elapsed

    batch_seconds_elapsed = await asyncio.gather(
        sleep(1),
        sleep(2),
        sleep(3),
    )

    assert batch_seconds_elapsed == pytest.approx([1, 2, 3], rel=TOLERANCE)
