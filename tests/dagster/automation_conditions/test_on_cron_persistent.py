from datetime import datetime
from functools import partial

import dagster as dg
import pytest

from yootils.dagster.automation_conditions import on_cron_persistent


@pytest.fixture(scope="module")
def cron_schedule() -> str:
    return "*/20 * * * *"


def test_no_lookback(instance: dg.DagsterInstance, cron_schedule: str) -> None:
    @dg.asset(
        automation_condition=on_cron_persistent(cron_schedule),
        # automation_condition=dg.AutomationCondition.on_cron(cron_schedule),
        partitions_def=dg.HourlyPartitionsDefinition(
            start_date=datetime(2025, 1, 1, 0, 0, 0), end_offset=1
        ),
    )
    def a() -> None:
        return

    evaluate = partial(dg.evaluate_automation_conditions, defs=[a], instance=instance)

    # Tick right before partition start
    result = evaluate(evaluation_time=datetime(2024, 12, 31, 23, 59, 30))
    assert result.total_requested == 0

    # Tick at first partition
    result = evaluate(
        evaluation_time=datetime(2025, 1, 1, 0, 0, 0),
        cursor=result.cursor,
    )
    assert result.total_requested == 1
    (partition_key,) = result.get_requested_partitions(dg.AssetKey("a"))
    assert partition_key == "2025-01-01-00:00"

    dg.materialize_to_memory([a], instance=instance, partition_key=partition_key)

    # Tick right after partition start
    result = evaluate(
        evaluation_time=datetime(2025, 1, 1, 0, 0, 30),
        cursor=result.cursor,
    )
    assert result.total_requested == 0

    # Tick at next cron trigger
    result = evaluate(
        evaluation_time=datetime(2025, 1, 1, 0, 20, 0),
        cursor=result.cursor,
    )
    assert result.total_requested == 0

    # Tick at cron trigger after that
    result = evaluate(
        evaluation_time=datetime(2025, 1, 1, 0, 40, 0),
        cursor=result.cursor,
    )
    assert result.total_requested == 0

    # Tick at next cron trigger and new partition is available
    result = evaluate(
        evaluation_time=datetime(2025, 1, 1, 1, 0, 0),
        cursor=result.cursor,
    )
    assert result.total_requested == 1
    assert result.get_requested_partitions(dg.AssetKey("a")) == {"2025-01-01-01:00"}
    
    # Tick at next cron trigger and new partition is available
    result = evaluate(
        evaluation_time=datetime(2025, 1, 1, 2, 0, 0),
        cursor=result.cursor,
    )
    assert result.total_requested == 1
    assert result.get_requested_partitions(dg.AssetKey("a")) == {"2025-01-01-02:00"}
