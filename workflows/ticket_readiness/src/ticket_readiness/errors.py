from __future__ import annotations


class TicketReadinessError(RuntimeError):
    """Base class for expected, operator-safe ticket readiness failures."""
