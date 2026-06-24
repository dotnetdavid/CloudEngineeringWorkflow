from __future__ import annotations

import time
from typing import Callable


class RateLimitError(RuntimeError):
    """Raised when an external API reports that requests are rate limited."""


class FixedDelayRateLimiter:
    def __init__(
        self,
        *,
        delay_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative.")
        self._delay_seconds = delay_seconds
        self._sleep = sleep

    def wait(self) -> None:
        if self._delay_seconds > 0:
            self._sleep(self._delay_seconds)
