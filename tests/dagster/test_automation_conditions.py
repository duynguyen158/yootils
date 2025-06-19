from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from typing import Any

import dagster as dg
import pytest
from dagster._core.definitions.declarative_automation.automation_condition_tester import (
    EvaluateAutomationConditionsResult,
)

from yootils.dagster.automation_conditions import (
    eager_persistent,
    on_cron_persistent as _on_cron_persistent,
)

on_cron_persistent = partial(_on_cron_persistent, cron_schedule="*/20 * * * *")


@pytest.fixture(scope="module")
def tick_step():
    return timedelta(minutes=5)


@pytest.fixture(scope="module")
def partitions_start():
    return datetime(2025, 1, 1, 0, 0, 0)


@pytest.fixture(scope="module")
def timestamp_start():
    return datetime(2024, 12, 31, 23, 40, 0)


@pytest.fixture(scope="function")
def instance() -> dg.DagsterInstance:
    return dg.DagsterInstance.ephemeral()


class AssetException(Exception):
    pass


@dataclass
class Tick:
    time: datetime
    partitions_requested: set[str]


@pytest.mark.parametrize(
    "automation_condition_factory, lookback_start, lookback_end, exception",
    [
        (
            on_cron_persistent,
            None,
            timedelta(hours=1),
            ValueError(
                "If lookback_end is specified, lookback_start must also be specified."
            ),
        ),
        (
            on_cron_persistent,
            timedelta(days=1),
            timedelta(days=1),
            ValueError("lookback_start must precede lookback_end"),
        ),
        (
            on_cron_persistent,
            timedelta(days=1),
            timedelta(days=2),
            ValueError("lookback_start must precede lookback_end"),
        ),
        (
            eager_persistent,
            None,
            timedelta(hours=1),
            ValueError(
                "If lookback_end is specified, lookback_start must also be specified."
            ),
        ),
        (
            eager_persistent,
            timedelta(days=1),
            timedelta(days=1),
            ValueError("lookback_start must precede lookback_end"),
        ),
        (
            eager_persistent,
            timedelta(days=1),
            timedelta(days=2),
            ValueError("lookback_start must precede lookback_end"),
        ),
    ],
)
def test_lookback_exceptions(
    automation_condition_factory: Callable[..., dg.AutomationCondition[Any]],
    lookback_start: timedelta | None,
    lookback_end: timedelta | None,
    exception: Exception,
) -> None:
    with pytest.raises(type(exception), match=str(exception)):
        automation_condition_factory(
            lookback_start=lookback_start, lookback_end=lookback_end
        )


@pytest.mark.parametrize(
    "automation_condition, partition_keys_to_fail, ticks_to_check",
    [
        (
            on_cron_persistent(),
            set(),
            [
                Tick(
                    time=datetime(2024, 12, 31, 23, 40, 0), partitions_requested=set()
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested={"2025-01-01-00:00"},
                ),
                Tick(time=datetime(2025, 1, 1, 0, 20, 0), partitions_requested=set()),
                Tick(time=datetime(2025, 1, 1, 0, 40, 0), partitions_requested=set()),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={"2025-01-01-01:00"},
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={"2025-01-01-02:00"},
                ),
            ],
        ),
        (
            on_cron_persistent(),
            {"2025-01-01-01:00"},  # Fail this partition
            [
                Tick(time=datetime(2024, 12, 31, 23, 40), partitions_requested=set()),
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested={"2025-01-01-00:00"},
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={"2025-01-01-01:00"},  # This will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 20, 0),
                    partitions_requested={
                        "2025-01-01-01:00"
                    },  # Next cron schedule, this will be re-requested
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 40, 0),
                    partitions_requested={
                        "2025-01-01-01:00"
                    },  # Next cron schedule, this will be re-requested
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={
                        "2025-01-01-02:00"
                    },  # Only new partition is requested (and the failed one isn't) since we're not looking back
                ),
            ],
        ),
        (
            on_cron_persistent(lookback_start=timedelta(hours=2)),
            {"2025-01-01-00:00", "2025-01-01-01:00"},  # Fail these partitions
            [
                Tick(time=datetime(2024, 12, 31, 23, 40), partitions_requested=set()),
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested={"2025-01-01-00:00"},  # This will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 20, 0),
                    partitions_requested={"2025-01-01-00:00"},  # This will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 40, 0),
                    partitions_requested={"2025-01-01-00:00"},  # This will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # These will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 20, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # These will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 40, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # These will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={
                        "2025-01-01-01:00",  # This will fail
                        "2025-01-01-02:00",
                    },
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 20, 0),
                    partitions_requested={
                        "2025-01-01-01:00",  # This will fail
                    },
                ),
            ],
        ),
        (
            on_cron_persistent(
                lookback_start=timedelta(hours=3),
                lookback_end=timedelta(hours=1),
            ),
            {"2025-01-01-00:00", "2025-01-01-01:00"},  # Fail these partitions
            [
                Tick(time=datetime(2024, 12, 31, 23, 40), partitions_requested=set()),
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested=set(),  # Since we implement a one-hour lag, this won't be requested till the next hour
                ),
                Tick(time=datetime(2025, 1, 1, 0, 20, 0), partitions_requested=set()),
                Tick(time=datetime(2025, 1, 1, 0, 40, 0), partitions_requested=set()),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={
                        "2025-01-01-00:00",  # This will fail
                    },
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 20, 0),
                    partitions_requested={
                        "2025-01-01-00:00",  # This will fail
                    },
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 40, 0),
                    partitions_requested={
                        "2025-01-01-00:00",  # This will fail
                    },
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # These will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 20, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # These will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 40, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # These will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 3, 0, 0),
                    partitions_requested={
                        "2025-01-01-01:00",  # This will fail
                        "2025-01-01-02:00",
                    },
                ),
                Tick(
                    time=datetime(2025, 1, 1, 3, 20, 0),
                    partitions_requested={
                        "2025-01-01-01:00",  # This will fail
                    },
                ),
            ],
        ),
        (
            eager_persistent(),
            set(),
            [
                # No tick to check before 2025-01-01 because realistically eager only kicks in after the timestamp of the first partition
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested=set(),  # Won't trigger because this is when the condition is applied
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 5, 0),
                    partitions_requested={
                        "2025-01-01-00:00"
                    },  # First partition is instead triggered at next tick
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={"2025-01-01-01:00"},
                ),
                Tick(time=datetime(2025, 1, 1, 1, 5, 0), partitions_requested=set()),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={"2025-01-01-02:00"},
                ),
            ],
        ),
        (
            eager_persistent(),
            {"2025-01-01-00:00", "2025-01-01-01:00"},
            [
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 5, 0),
                    partitions_requested={"2025-01-01-00:00"},  # This will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 10, 0),
                    partitions_requested={"2025-01-01-00:00"},  # This will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={
                        "2025-01-01-01:00"
                    },  # This will fail. Previous partition is ignore since we're not looking back.
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 5, 0),
                    partitions_requested={
                        "2025-01-01-01:00"
                    },  # This will fail. Previous partition is ignore since we're not looking back.
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={"2025-01-01-02:00"},
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 5, 0),
                    partitions_requested=set(),
                ),
            ],
        ),
        (
            eager_persistent(lookback_start=timedelta(hours=2)),
            {"2025-01-01-00:00", "2025-01-01-01:00"},
            [
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 5, 0),
                    partitions_requested={"2025-01-01-00:00"},  # This will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # These will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 5, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # These will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={
                        "2025-01-01-01:00",  # This will fail
                        "2025-01-01-02:00",
                    },  # 00:00 is dropped since it's no longer in the window
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 5, 0),
                    partitions_requested={"2025-01-01-01:00"},
                ),
                Tick(
                    time=datetime(2025, 1, 1, 3, 0, 0),
                    partitions_requested={
                        "2025-01-01-03:00"
                    },  # 01:00 is dropped since it's no longer in the window
                ),
                Tick(
                    time=datetime(2025, 1, 1, 3, 5, 0),
                    partitions_requested=set(),
                ),
            ],
        ),
        (
            eager_persistent(
                lookback_start=timedelta(hours=3), lookback_end=timedelta(hours=1)
            ),
            {"2025-01-01-00:00", "2025-01-01-01:00"},
            [
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 5, 0),
                    partitions_requested=set(),  # Since we implement a one-hour lag, this won't be requested till the next hour
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                    },  # This will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 5, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                    },  # This will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # These will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 5, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # These will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 3, 0, 0),
                    partitions_requested={
                        "2025-01-01-01:00",  # This will fail
                        "2025-01-01-02:00",
                    },  # 00:00 is dropped since it's no longer in the window
                ),
                Tick(
                    time=datetime(2025, 1, 1, 3, 5, 0),
                    partitions_requested={"2025-01-01-01:00"},  # This will fail
                ),
            ],
        ),
    ],
    ids=[
        "on_cron_persistent_no_lookback",
        "on_cron_persistent_no_lookback_failed",
        "on_cron_persistent_with_lookback",
        "on_cron_persistent_with_lagged_lookback",
        "eager_persistent_no_lookback",
        "eager_persistent_no_lookback_failed",
        "eager_persistent_with_lookback",
        "eager_persistent_with_lagged_lookback",
    ],
)
def test_with_asset_no_deps(
    instance: dg.DagsterInstance,
    tick_step: timedelta,
    partitions_start: datetime,
    timestamp_start: datetime,
    automation_condition: dg.AutomationCondition[Any],
    partition_keys_to_fail: set[str],
    ticks_to_check: Sequence[Tick],
) -> None:
    @dg.asset(
        automation_condition=automation_condition,
        partitions_def=dg.HourlyPartitionsDefinition(
            start_date=partitions_start, end_offset=1
        ),
    )
    def asset_single(context: dg.AssetExecutionContext) -> None:
        if (partition_key := context.partition_key) in partition_keys_to_fail:
            raise AssetException(f"Failed on purpose for partition {partition_key}")

    timestamp: datetime = timestamp_start
    _ticks_to_check = {t.time: t for t in ticks_to_check}

    result: EvaluateAutomationConditionsResult | None = None

    while len(_ticks_to_check) > 0:
        result = dg.evaluate_automation_conditions(
            defs=[asset_single],
            instance=instance,
            evaluation_time=timestamp,
            cursor=result.cursor if result is not None else None,
        )

        if timestamp in _ticks_to_check:
            tick = _ticks_to_check.pop(timestamp)

            partition_keys_requested = result.get_requested_partitions(
                dg.AssetKey("asset_single")
            )
            assert partition_keys_requested == tick.partitions_requested

            for partition_key in partition_keys_requested:
                dg.materialize_to_memory(
                    [asset_single],
                    instance=instance,
                    partition_key=partition_key,
                    raise_on_error=False,
                )

        timestamp += tick_step
