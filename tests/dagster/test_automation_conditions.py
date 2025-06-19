from collections import defaultdict
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
from freezegun import freeze_time

from yootils.dagster.automation_conditions import (
    eager_persistent,
    on_cron_persistent as _on_cron_persistent,
)
from yootils.datetime.utcnow import utcnow

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


@pytest.fixture(scope="module")
def hourly_partitions_definition(
    partitions_start: datetime,
) -> dg.HourlyPartitionsDefinition:
    return dg.HourlyPartitionsDefinition(start_date=partitions_start, end_offset=1)


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
    [
        "automation_condition_factory",
        "lookback_start",
        "lookback_end",
        "exception",
    ],
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
    [
        "automation_condition",
        "partition_keys_to_fail",
        "ticks_to_check",
    ],
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
    timestamp_start: datetime,
    hourly_partitions_definition: dg.HourlyPartitionsDefinition,
    automation_condition: dg.AutomationCondition[Any],
    partition_keys_to_fail: set[str],
    ticks_to_check: Sequence[Tick],
) -> None:
    @dg.asset(
        automation_condition=automation_condition,
        partitions_def=hourly_partitions_definition,
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


@pytest.mark.parametrize(
    [
        "upstream_automation_condition",
        "downstream_automation_condition",
        "upstream_partition_keys_to_fail_to_recovery_latency",
        "downstream_ticks_to_check",
    ],
    [
        (
            on_cron_persistent(),
            eager_persistent(),
            set(),
            [
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested={"2025-01-01-00:00"},
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 5, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 20, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 40, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={"2025-01-01-01:00"},
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 5, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 20, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 40, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={"2025-01-01-02:00"},
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 5, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 20, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 40, 0),
                    partitions_requested=set(),
                ),
            ],
        ),
        (
            on_cron_persistent(),
            eager_persistent(),
            {
                "2025-01-01-01:00": timedelta(minutes=20)
            },  # Fail this partition for upstream
            [
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested={"2025-01-01-00:00"},
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 5, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 20, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 40, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={"2025-01-01-01:00"},  # Upstream will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 5, 0),
                    partitions_requested=set(),  # Isn't requested because upstream failed
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 20, 0),
                    partitions_requested={"2025-01-01-01:00"},  # Upstream will succeed
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 25, 0),
                    partitions_requested=set(),  # Isn't requested because upstream succeeded
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 40, 0),
                    partitions_requested=set(),  # Isn't requested because upstream succeeded and this succeeded
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={"2025-01-01-02:00"},
                ),
                Tick(time=datetime(2025, 1, 1, 2, 5, 0), partitions_requested=set()),
            ],
        ),
        (
            on_cron_persistent(lookback_start=timedelta(hours=2)),
            eager_persistent(lookback_start=timedelta(hours=2)),
            {
                "2025-01-01-00:00": timedelta(hours=1, minutes=20),
                "2025-01-01-01:00": timedelta(minutes=30),
            },  # Fail these partitions for upstream and recover after these timedeltas
            [
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested={"2025-01-01-00:00"},  # Upstream will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 5, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 20, 0),
                    partitions_requested={"2025-01-01-00:00"},  # Upstream will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 40, 0),
                    partitions_requested={"2025-01-01-00:00"},  # Upstream will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # Upstream will fail for both partitions
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 5, 0),
                    partitions_requested=set(),  # Isn't requested because upstream failed for both partitions
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 20, 0),
                    partitions_requested={
                        "2025-01-01-00:00",  # Upstream will succeed
                        "2025-01-01-01:00",  # Upstream will fail
                    },
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 25, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 40, 0),
                    partitions_requested={
                        "2025-01-01-01:00"  # Upstream will succeed
                    },
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 45, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={"2025-01-01-02:00"},
                ),
                Tick(time=datetime(2025, 1, 1, 2, 5, 0), partitions_requested=set()),
            ],
        ),
        (
            on_cron_persistent(
                lookback_start=timedelta(hours=3), lookback_end=timedelta(hours=1)
            ),
            eager_persistent(
                lookback_start=timedelta(hours=3), lookback_end=timedelta(hours=1)
            ),
            {
                "2025-01-01-00:00": timedelta(hours=2, minutes=20),
                "2025-01-01-01:00": timedelta(hours=1, minutes=30),
            },  # Fail these partitions for upstream and recover after these timedeltas
            [
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 5, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 20, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 40, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={"2025-01-01-00:00"},  # Upstream will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 5, 0),
                    partitions_requested=set(),  # Isn't requested because upstream failed for both partitions
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 20, 0),
                    partitions_requested={"2025-01-01-00:00"},  # Upstream will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 25, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 40, 0),
                    partitions_requested={"2025-01-01-00:00"},  # Upstream will fail
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={
                        "2025-01-01-00:00",
                        "2025-01-01-01:00",
                    },  # Upstream will fail for both partitions
                ),
                Tick(time=datetime(2025, 1, 1, 2, 5, 0), partitions_requested=set()),
                Tick(
                    time=datetime(2025, 1, 1, 2, 20, 0),
                    partitions_requested={
                        "2025-01-01-00:00",  # Upstream will succeed
                        "2025-01-01-01:00",  # Upstream will fail
                    },
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 25, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 40, 0),
                    partitions_requested={
                        "2025-01-01-01:00"  # Upstream will succeed
                    },
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 45, 0),
                    partitions_requested=set(),
                ),
                Tick(
                    time=datetime(2025, 1, 1, 3, 0, 0),
                    partitions_requested={"2025-01-01-02:00"},
                ),
                Tick(time=datetime(2025, 1, 1, 3, 5, 0), partitions_requested=set()),
            ],
        ),
    ],
    ids=[
        "no_lookback",
        "no_lookback_failed",
        "with_lookback",
        "with_lagged_lookback",
    ],
)
def test_with_asset_with_deps(
    instance: dg.DagsterInstance,
    tick_step: timedelta,
    timestamp_start: datetime,
    hourly_partitions_definition: dg.HourlyPartitionsDefinition,
    upstream_automation_condition: dg.AutomationCondition[Any],
    downstream_automation_condition: dg.AutomationCondition[Any],
    upstream_partition_keys_to_fail_to_recovery_latency: dict[str, timedelta],
    downstream_ticks_to_check: Sequence[Tick],
) -> None:
    with freeze_time(datetime(2025, 1, 1, 0, 0, 0)) as frozen_time:

        @dg.asset(
            automation_condition=upstream_automation_condition,
            partitions_def=hourly_partitions_definition,
        )
        def asset_upstream(context: dg.AssetExecutionContext) -> int:
            if (
                (partition_key := context.partition_key)
                in upstream_partition_keys_to_fail_to_recovery_latency
                and utcnow()
                < context.partition_time_window.start
                + upstream_partition_keys_to_fail_to_recovery_latency[partition_key]
            ):
                raise AssetException(
                    f"Failed on purpose for partition {partition_key} of asset_upstream"
                )

            return 42

        @dg.asset(
            automation_condition=downstream_automation_condition,
            partitions_def=hourly_partitions_definition,
        )
        def asset_downstream(
            context: dg.AssetExecutionContext, asset_upstream: int
        ) -> None:
            return

        timestamp: datetime = timestamp_start
        frozen_time.move_to(timestamp)

        _downstream_ticks_to_check = {t.time: t for t in downstream_ticks_to_check}

        result: EvaluateAutomationConditionsResult | None = None

        while len(_downstream_ticks_to_check) > 0:
            result = dg.evaluate_automation_conditions(
                defs=[asset_upstream, asset_downstream],
                instance=instance,
                evaluation_time=timestamp,
                cursor=result.cursor if result is not None else None,
            )

            if timestamp in _downstream_ticks_to_check:
                tick = _downstream_ticks_to_check.pop(timestamp)

                upstream_partition_keys_requested = result.get_requested_partitions(
                    dg.AssetKey("asset_upstream")
                )
                downstream_partition_keys_requested = result.get_requested_partitions(
                    dg.AssetKey("asset_downstream")
                )

                assert downstream_partition_keys_requested == tick.partitions_requested

                partition_keys_requested: defaultdict[
                    str, list[dg.AssetsDefinition]
                ] = defaultdict(list)

                for partition_key in upstream_partition_keys_requested:
                    assert partition_key is not None, "This should not happen"
                    partition_keys_requested[partition_key].append(asset_upstream)

                for partition_key in downstream_partition_keys_requested:
                    assert partition_key is not None, "This should not happen"
                    partition_keys_requested[partition_key].append(asset_downstream)

                for partition_key, assets in sorted(partition_keys_requested.items()):
                    dg.materialize_to_memory(
                        assets,
                        instance=instance,
                        partition_key=partition_key,
                        raise_on_error=False,
                    )

            timestamp += tick_step
            frozen_time.move_to(timestamp)
