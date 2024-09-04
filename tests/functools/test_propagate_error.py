from yootils.functools.propagate_error import Success, propagate_error


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
