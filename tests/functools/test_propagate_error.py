import pytest

from yootils.functools.propagate_error import (
    Success,
    propagate_error,
    propagate_error_async,
)


class ThisShouldNotHappen(Exception):
    pass


def test_success() -> None:
    @propagate_error[Exception]()
    def func(x: int) -> int:
        return x + 1

    match func(1):
        case Success(value):
            assert value == 2
        # Important boilerplate that says all uncaught exceptions should be raised, and raised explicitly, though in this trivial example we'll never reach this point.
        # BEST PRACTICE: Always include this boilerplate in your match statements to raise uncaught exceptions.
        # `case Exception() as uncaught_exception:` will also work
        case uncaught_exception:
            raise uncaught_exception


def test_failure_caught_exception() -> None:
    @propagate_error[ZeroDivisionError]()
    def func(x: float) -> float:
        return 1 / x

    match func(0):
        case Success(_):
            raise ThisShouldNotHappen()
        case ZeroDivisionError():
            pass
        case uncaught_exception:
            raise uncaught_exception


def test_failure_uncaught_exception() -> None:
    @propagate_error[ZeroDivisionError]()
    def func(x: float) -> float:
        raise ValueError("Uncaught exception")
        return 1 / x

    match func(0):
        case Success(_):
            raise ThisShouldNotHappen()
        case ZeroDivisionError():
            raise ThisShouldNotHappen()
        case uncaught_exception:
            with pytest.raises(ValueError, match="Uncaught exception"):
                raise uncaught_exception


@pytest.mark.asyncio
async def test_async_success() -> None:
    @propagate_error_async[Exception]()
    async def func(x: int) -> int:
        return x + 1

    match await func(1):
        case Success(value):
            assert value == 2
        # Trivial; we'll never reach this point.
        # Interestingly, doing this is fine with mypy but `case uncaught_exception:` makes mypy complain "error: Exception must be derived from BaseException," which doesn't happen in the synchronous version.
        case Exception() as uncaught_exception:
            raise uncaught_exception


@pytest.mark.asyncio
async def test_async_failure_caught_exception() -> None:
    @propagate_error_async[ZeroDivisionError]()
    async def func(x: float) -> float:
        return 1 / x

    match await func(0):
        case Success(_):
            raise ThisShouldNotHappen()
        case ZeroDivisionError():
            pass
        case Exception() as uncaught_exception:
            raise uncaught_exception


@pytest.mark.asyncio
async def test_async_failure_uncaught_exception() -> None:
    @propagate_error_async[ZeroDivisionError]()
    async def func(x: float) -> float:
        raise ValueError("Uncaught exception")
        return 1 / x

    match await func(0):
        case Success(_):
            raise ThisShouldNotHappen()
        case ZeroDivisionError():
            raise ThisShouldNotHappen()
        case Exception() as uncaught_exception:
            with pytest.raises(ValueError, match="Uncaught exception"):
                raise uncaught_exception
