from datetime import timedelta

from dagster import AutomationCondition
from dagster._core.definitions.asset_key import T_EntityKey
from dagster._core.definitions.declarative_automation import AndAutomationCondition


def _validate_lookback_range(
    start: timedelta | None, end: timedelta | None
) -> AutomationCondition[T_EntityKey]:
    match (start, end):
        case (None, timedelta()):
            raise ValueError(
                "If lookback_end is specified, lookback_start must also be specified."
            )
        case (timedelta(), timedelta()) if end.total_seconds() >= start.total_seconds():
            raise ValueError("lookback_start must precede lookback_end")
        case (timedelta(), timedelta()):
            window = AutomationCondition.in_latest_time_window(
                lookback_delta=start
            ) & ~AutomationCondition.in_latest_time_window(lookback_delta=end)
        case (timedelta(), None):
            window = AutomationCondition.in_latest_time_window(lookback_delta=start)
        case (None, None):
            window = AutomationCondition.in_latest_time_window()

    return window


def on_cron_persistent(
    cron_schedule: str,
    cron_timezone: str = "UTC",
    lookback_start: timedelta | None = None,
    lookback_end: timedelta | None = None,
) -> AndAutomationCondition[T_EntityKey]:
    """
    Returns an AutomationCondition that triggers asset execution on a given cron schedule until the asset is successfully materialized.

    If the asset is time-partitioned, unlike `AutomationCondition.on_cron`, multiple time partitions can be considered by setting `lookback_start` and `lookback_end` to the desired timedelta values (relative to the partition time).

    Args:
        cron_schedule (str): Cron schedule for the automation condition.
        cron_timezone (str): Timezone for the cron schedule. Defaults to "UTC".
        lookback_start (timedelta | None): Start of the lookback window. Defaults to None.
        lookback_end (timedelta | None): End of the lookback window. Defaults to None.

    Returns:
        AndAutomationCondition[T_EntityKey]: The returned AutomationCondition.
    """
    window = _validate_lookback_range(lookback_start, lookback_end)

    return (
        window
        & AutomationCondition.cron_tick_passed(
            cron_schedule, cron_timezone
        ).since_last_handled()
        & AutomationCondition.all_deps_updated_since_cron(cron_schedule, cron_timezone)
        & ~AutomationCondition.in_progress()
        & (AutomationCondition.missing() | AutomationCondition.execution_failed())
    ).with_label("on_cron_persistent")


def eager_persistent(
    lookback_start: timedelta | None = None, lookback_end: timedelta | None = None
) -> AndAutomationCondition[T_EntityKey]:
    """
    Returns an AutomationCondition which will cause a target to be executed if any of
    its dependencies update, and will execute missing partitions if they become missing
    after this condition is applied to the target.

    This will not execute targets that have any missing or in progress dependencies, or
    are currently in progress. But, unlike `AutomationCondition.eager`, it will also execute
    targets that just failed.

    For time partitioned assets, unlike `AutomationCondition.eager`, multiple time partitions can be considered by setting `lookback_start` and `lookback_end` to the desired timedelta values (relative to the partition time).

    Args:
        lookback_start (timedelta | None): Start of the lookback window. Defaults to None.
        lookback_end (timedelta | None): End of the lookback window. Defaults to None.

    Returns:
        AndAutomationCondition[T_EntityKey]: The returned AutomationCondition.
    """
    window = _validate_lookback_range(lookback_start, lookback_end)

    return (
        window
        & (
            AutomationCondition.missing().since_last_handled()
            | AutomationCondition.any_deps_updated().since_last_handled()
            | AutomationCondition.execution_failed()
        )
        & ~AutomationCondition.any_deps_missing()
        & ~AutomationCondition.any_deps_in_progress()
        & ~AutomationCondition.in_progress()
    ).with_label("eager_persistent")
