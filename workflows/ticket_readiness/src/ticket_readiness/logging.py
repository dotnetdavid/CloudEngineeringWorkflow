from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

LOGGER_NAME = "ticket_readiness"


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "severity": record.levelname.lower(),
            "message": record.getMessage(),
        }
        for field_name in ("event_type", "run_id", "issue_id", "state"):
            value = getattr(record, field_name, None)
            if value is not None:
                payload[field_name] = value
        return json.dumps(payload, sort_keys=True)


def configure_logging() -> None:
    """Configure stderr JSON logging for CLI and artifact events."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_event(
    *,
    event_type: str,
    state: str,
    message: str,
    run_id: str | None = None,
    issue_id: str | None = None,
    severity: str = "info",
) -> None:
    """Emit a structured operational event to the workflow logger."""
    logger = logging.getLogger(LOGGER_NAME)
    level = logging.ERROR if severity == "error" else logging.INFO
    logger.log(
        level,
        message,
        extra={
            "event_type": event_type,
            "state": state,
            "run_id": run_id,
            "issue_id": issue_id,
        },
    )
