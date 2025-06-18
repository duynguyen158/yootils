from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import dagster as dg
import pytest
from dagster._core.definitions.declarative_automation.automation_condition_tester import (
    EvaluateAutomationConditionsResult,
)

from yootils.dagster.automation_conditions import on_cron_persistent

CRON_SCHEDULE = "*/20 * * * *"


@pytest.fixture(scope="module")
def tick_step():
    return timedelta(seconds=300)


@pytest.fixture(scope="module")
def partitions_start():
    return datetime(2024, 1, 1, 0, 0, 0)


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
    materialize: bool = False


@pytest.mark.parametrize(
    "automation_condition,partition_keys_to_fail,ticks_to_check",
    [
        (
            on_cron_persistent(CRON_SCHEDULE),
            set(),
            [
                Tick(
                    time=datetime(2024, 12, 31, 23, 40, 0), partitions_requested=set()
                ),
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested={"2025-01-01-00:00"},
                    materialize=True,
                ),
                Tick(time=datetime(2025, 1, 1, 0, 20, 0), partitions_requested=set()),
                Tick(time=datetime(2025, 1, 1, 0, 40, 0), partitions_requested=set()),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={"2025-01-01-01:00"},
                    materialize=True,
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={"2025-01-01-02:00"},
                    materialize=True,
                ),
            ],
        ),
        (
            on_cron_persistent(CRON_SCHEDULE),
            {"2025-01-01-01:00"},  # Fail this partition
            [
                Tick(time=datetime(2024, 12, 31, 23, 40), partitions_requested=set()),
                Tick(
                    time=datetime(2025, 1, 1, 0, 0, 0),
                    partitions_requested={"2025-01-01-00:00"},
                    materialize=True,
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 0, 0),
                    partitions_requested={"2025-01-01-01:00"},  # This will fail
                    materialize=True,
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 20, 0),
                    partitions_requested={
                        "2025-01-01-01:00"
                    },  # Next cron schedule, this will be re-requested
                    materialize=True,
                ),
                Tick(
                    time=datetime(2025, 1, 1, 1, 40, 0),
                    partitions_requested={
                        "2025-01-01-01:00"
                    },  # Next cron schedule, this will be re-requested
                    materialize=True,
                ),
                Tick(
                    time=datetime(2025, 1, 1, 2, 0, 0),
                    partitions_requested={
                        "2025-01-01-02:00"
                    },  # Only new partition is requested (and the failed one isn't) since we're not looking back
                    materialize=True,
                ),
            ],
        ),
        # (
        #     on_cron_persistent(CRON_SCHEDULE, lookback_start=timedelta(hours=2)),
        #     {"2025-01-01-00:00" ,"2025-01-01-01:00"},  # Fail this partition
        #     [
        #         Tick(time=datetime(2024, 12, 31, 23, 40), partitions_requested=set()),
        #         Tick(
        #             time=datetime(2025, 1, 1, 0, 0, 0),
        #             partitions_requested={"2025-01-01-00:00"}, # This will fail
        #             materialize=True,
        #         ),
        #         Tick(time=datetime(2025, 1, 1, 0, 0, 30), partitions_requested=set()),
        #         Tick(
        #             time=datetime(2025, 1, 1, 1, 0, 0),
        #             partitions_requested={"2025-01-01-01:00"},  # This will fail
        #             materialize=True,
        #         ),
        #         Tick(
        #             time=datetime(2025, 1, 1, 1, 0, 30),
        #             partitions_requested=set(),
        #         ),
        #         Tick(
        #             time=datetime(2025, 1, 1, 1, 20, 0),
        #             partitions_requested={
        #                 "2025-01-01-01:00"
        #             },  # Next cron schedule, this will be re-requested
        #             materialize=True,
        #         ),
        #         Tick(
        #             time=datetime(2025, 1, 1, 1, 20, 30),
        #             partitions_requested=set(),
        #         ),
        #         Tick(
        #             time=datetime(2025, 1, 1, 2, 0, 0),
        #             partitions_requested={
        #                 "2025-01-01-02:00"
        #             },  # Only new partition is requested (and the failed one isn't) since we're not looking back
        #             materialize=True,
        #         ),
        #     ],
        # ),
    ],
    ids=["on_cron_persistent_no_lookback", "on_cron_persistent_no_lookback_failed"],
)
def test_automation_condition_single_asset(
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
    def a(context: dg.AssetExecutionContext) -> None:
        if (partition_key := context.partition_key) in partition_keys_to_fail:
            raise AssetException(f"Failed on purpose for partition {partition_key}")

    timestamp: datetime = timestamp_start
    _ticks_to_check = {t.time: t for t in ticks_to_check}

    result: EvaluateAutomationConditionsResult | None = None

    while len(_ticks_to_check) > 0:
        result = dg.evaluate_automation_conditions(
            defs=[a],
            instance=instance,
            evaluation_time=timestamp,
            cursor=result.cursor if result is not None else None,
        )

        if timestamp in _ticks_to_check:
            tick = _ticks_to_check.pop(timestamp)

            partition_keys_requested = result.get_requested_partitions(dg.AssetKey("a"))
            assert partition_keys_requested == tick.partitions_requested

            if tick.materialize:
                for partition_key in partition_keys_requested:
                    dg.materialize_to_memory(
                        [a],
                        instance=instance,
                        partition_key=partition_key,
                        raise_on_error=False,
                    )

        timestamp += tick_step
