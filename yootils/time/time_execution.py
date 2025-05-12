from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    asynccontextmanager,
    contextmanager,
)
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Generic, Literal, TypeVar, cast


class _TimerState(IntEnum):
    """
    Enum that represents the state of a timer.
    """

    STARTED = auto()
    STOPPED = auto()


_S = TypeVar("_S", bound=_TimerState)


@dataclass(slots=True)
class _Timer(Generic[_S]):
    """
    Class that times the execution of a block of code and stores seconds elapsed.
    Uses typestate pattern to discourage (but not prevent) it from being used more than once.
    """

    seconds_elapsed: float = 0

    @contextmanager
    def __call__(
        self: _Timer[Literal[_TimerState.STARTED]],
    ) -> Iterator[_Timer[Literal[_TimerState.STOPPED]]]:
        """
        Times the execution.

        Yields:
            Iterator[_Timer[Literal[_TimerState.STOPPED]]]: The timer instance.
        """
        start = time.perf_counter()
        try:
            yield cast(_Timer[Literal[_TimerState.STOPPED]], self)
        finally:
            end = time.perf_counter()
            self.seconds_elapsed = end - start


@dataclass(slots=True)
class _AsyncTimer(Generic[_S]):
    """
    Class that times the execution of an asynchronous block of code and stores seconds elapsed.
    Uses typestate pattern to discourage (but not prevent) it from being used more than once.
    """

    seconds_elapsed: float = 0

    @asynccontextmanager
    async def __call__(
        self: _AsyncTimer[Literal[_TimerState.STARTED]],
    ) -> AsyncIterator[_AsyncTimer[Literal[_TimerState.STOPPED]]]:
        """
        Times the execution.

        Yields:
            AsyncIterator[_AsyncTimer[Literal[_TimerState.STOPPED]]]: The timer instance.
        """
        loop = asyncio.get_event_loop()
        start = loop.time()
        try:
            yield cast(_AsyncTimer[Literal[_TimerState.STOPPED]], self)
        finally:
            end = loop.time()
            self.seconds_elapsed = end - start


def time_execution() -> AbstractContextManager[_Timer[Literal[_TimerState.STOPPED]]]:
    """
    Times the execution of a block of code and returns the Timer instance.
    """
    return _Timer[Literal[_TimerState.STARTED]]()()


def time_execution_async() -> AbstractAsyncContextManager[
    _AsyncTimer[Literal[_TimerState.STOPPED]]
]:
    """
    Times the execution of an asynchronous block of code and returns the AsyncTimer instance.
    """
    return _AsyncTimer[Literal[_TimerState.STARTED]]()()
