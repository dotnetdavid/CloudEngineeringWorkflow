from __future__ import annotations

from numbers import Real

from ticket_readiness.security import redact_secrets

MAX_ERROR_DETAIL_LENGTH = 500
MAX_TIMEOUT_SECONDS = 300


def validate_timeout_seconds(timeout_seconds: Real, *, field_name: str = "timeout_seconds") -> Real:
    """Validate bounded HTTP timeout values supplied to API clients."""
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, Real):
        raise ValueError(f"{field_name} must be a number of seconds.")
    if timeout_seconds <= 0:
        raise ValueError(f"{field_name} must be greater than 0.")
    if timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise ValueError(f"{field_name} must be less than or equal to {MAX_TIMEOUT_SECONDS}.")
    return timeout_seconds


def safe_http_error_detail(body: bytes) -> str:
    """Return a bounded, redacted HTTP error body for operator logs."""
    detail = body.decode("utf-8", errors="replace")[:MAX_ERROR_DETAIL_LENGTH]
    return str(redact_secrets(detail))
