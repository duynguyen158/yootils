from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
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

    seconds: float = 0

    @contextmanager
    def __call__(self: _Timer[Literal[_TimerState.STARTED]]) -> Iterator[_Timer[Literal[_TimerState.STOPPED]]]:
        """Times the execution.

        Yields:
            Iterator[_Timer[Literal[_TimerState.STOPPED]]]: The timer instance.
        """
        start = time.perf_counter()
        try:
            yield cast(_Timer[Literal[_TimerState.STOPPED]], self)
        finally:
            end = time.perf_counter()
            self.seconds = end - start


def time_execution() -> AbstractContextManager[_Timer[Literal[_TimerState.STOPPED]]]:
    """
    Times the execution of a block of code and returns the Timer instance.
    """
    return _Timer[Literal[_TimerState.STARTED]]()()
