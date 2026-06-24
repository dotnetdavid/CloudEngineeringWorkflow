from __future__ import annotations

import re
from typing import Any

REDACTION = "[REDACTED_SECRET]"

SECRET_PATTERNS = (
    re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
        re.DOTALL,
    ),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(
        r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|rediss|sqlserver)://[^\s'\"<>]+"
    ),
    re.compile(r"(?i)\bjdbc:(?:postgresql|mysql|mariadb|sqlserver):[^\s'\"<>]+"),
    re.compile(
        r"(?i)\b(?:server|data source|host)\s*=[^;\n]+;(?:[^;\n]*;)*\s*(?:password|pwd)\s*=[^;\n]+(?:;[^;\n]*)*"
    ),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*[A-Za-z0-9._/+=-]{20,}"),
    re.compile(r"(?i)\baws_secret_access_key\s*[:=]\s*[A-Za-z0-9/+=]{20,}"),
)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, str):
        redacted = value
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub(_replacement, redacted)
        return redacted

    if isinstance(value, dict):
        return {key: redact_secrets(item) for key, item in value.items()}

    if isinstance(value, list):
        return [redact_secrets(item) for item in value]

    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)

    return value


def contains_secret_like_value(value: Any) -> bool:
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in SECRET_PATTERNS)
    if isinstance(value, dict):
        return any(contains_secret_like_value(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(contains_secret_like_value(item) for item in value)
    return False


def _replacement(match: re.Match[str]) -> str:
    value = match.group(0)
    if "=" in value:
        return f"{value.split('=', 1)[0]}={REDACTION}"
    if ":" in value:
        return f"{value.split(':', 1)[0]}: {REDACTION}"
    if value.lower().startswith("bearer "):
        return f"Bearer {REDACTION}"
    return REDACTION
