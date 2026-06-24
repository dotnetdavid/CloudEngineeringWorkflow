from __future__ import annotations

from numbers import Real

MAX_TIMEOUT_SECONDS = 300


def validate_timeout_seconds(timeout_seconds: Real, *, field_name: str = "timeout_seconds") -> Real:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, Real):
        raise ValueError(f"{field_name} must be a number of seconds.")
    if timeout_seconds <= 0:
        raise ValueError(f"{field_name} must be greater than 0.")
    if timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise ValueError(f"{field_name} must be less than or equal to {MAX_TIMEOUT_SECONDS}.")
    return timeout_seconds
