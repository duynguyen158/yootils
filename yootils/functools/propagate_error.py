from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from typing import Generic, ParamSpec, TypeVar

_P = ParamSpec("_P")
_R = TypeVar("_R")
_E = TypeVar("_E", bound=Exception)


@dataclass
class Success(Generic[_R]):
    """
    Wrapper class for successful function calls.
    """

    value: _R


class propagate_error(Generic[_E]):
    """
    Decorator that wraps a function and returns a Success instance if the function runs successfully, or an exception if it fails.
    The exception type is specified as a type argument, used to type hint the return value of the decorated function for downstream match statements. (See the corresponding test for usage.)
    """

    def __call__(
        self, func: Callable[_P, _R]
    ) -> Callable[_P, Success[_R] | _E | Exception]:
        """Inner decorator that wraps the function and returns a Success instance if the function runs successfully, or an exception if it fails.

        Args:
            func (Callable[_P, _R]): The function to be wrapped.

        Returns:
            Callable[_P, Success[_R] | _E | Exception]: The wrapped function.
        """

        @wraps(func)
        def wrapper(
            *args: _P.args, **kwargs: _P.kwargs
        ) -> Success[_R] | _E | Exception:
            try:
                return Success(func(*args, **kwargs))
            except Exception as e:
                return e

        return wrapper


class propagate_error_async(Generic[_E]):
    """
    Error-propagation decorator for async functions.
    """

    def __call__(
        self, func: Callable[_P, Awaitable[_R]]
    ) -> Callable[_P, Awaitable[Success[_R] | _E | Exception]]:
        """
        Inner decorator that wraps the async function and returns a Success instance if the function runs successfully, or an exception if it fails.

        Args:
            func (Callable[_P, Awaitable[_R]]): The async function to be wrapped.

        Returns:
            Callable[_P, Awaitable[Success[_R] | _E | Exception]]: The wrapped async function.
        """

        @wraps(func)
        async def wrapper(
            *args: _P.args, **kwargs: _P.kwargs
        ) -> Success[_R] | _E | Exception:
            try:
                return Success(await func(*args, **kwargs))
            except Exception as e:
                return e

        return wrapper
