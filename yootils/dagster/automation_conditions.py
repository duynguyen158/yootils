from datetime import timedelta

from dagster import AutomationCondition
from dagster._core.definitions.asset_key import T_EntityKey
from dagster._core.definitions.declarative_automation import AndAutomationCondition


def on_cron_persistent(
    cron_schedule: str,
    cron_timezone: str = "UTC",
    lookback_start: timedelta | None = None,
    lookback_end: timedelta | None = None,
) -> AndAutomationCondition[T_EntityKey]:
    """
    Returns an AutomationCondition that triggers asset execution on a given cron schedule until the asset is successfully materialized.

    If the asset is time-partitioned, unlike `AutomationCondition.on_cron`, multiple time partitions can be considered by setting `lookback_start` and `lookback_end` to the desired timedelta values (relative to the partition time).
    """
    match (lookback_start, lookback_end):
        case (None, timedelta()):
            raise ValueError(
                "If lookback_end is specified, lookback_start must also be specified."
            )
        case (timedelta(), timedelta()) if (
            lookback_end.total_seconds() >= lookback_start.total_seconds()
        ):
            raise ValueError("lookback_start must precede lookback_end")
        case (timedelta(), timedelta()):
            window = AutomationCondition.in_latest_time_window(
                lookback_delta=lookback_start
            ) & ~AutomationCondition.in_latest_time_window(lookback_delta=lookback_end)
        case (timedelta(), None):
            window = AutomationCondition.in_latest_time_window(
                lookback_delta=lookback_start
            )
        case (None, None):
            window = AutomationCondition.in_latest_time_window()

    return (
        AutomationCondition.on_cron(cron_schedule, cron_timezone).replace(
            AutomationCondition.in_latest_time_window(),
            window,
        )
        & ~AutomationCondition.in_progress()
        & (AutomationCondition.missing() | AutomationCondition.execution_failed())
    ).with_label("on_cron_persistent")
