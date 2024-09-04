from yootils.functools.propagate_error import Success, propagate_error


class ThisShouldNotHappen(Exception):
    pass


def test_success() -> None:
    @propagate_error[Exception]()
    def func(x: int) -> int:
        return x + 1

    match func(1):
        case Success(value):
            assert value == 2
        # Important boilerplate that says all uncaught exceptions should be raised, and raised explicitly,
        # though in this trivial example we'll never reach this point.
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
            assert isinstance(uncaught_exception, ValueError)
            assert str(uncaught_exception) == "Uncaught exception"
