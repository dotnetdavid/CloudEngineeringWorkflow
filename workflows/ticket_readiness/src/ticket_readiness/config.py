from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ticket_readiness.errors import TicketReadinessError


class ConfigError(TicketReadinessError):
    """Raised when workflow configuration cannot be loaded or trusted."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file and require a top-level mapping."""
    config_path = Path(path)
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
    except OSError as exc:
        raise ConfigError(f"Failed to read config file: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Config file is not valid YAML: {config_path}") from exc

    if not isinstance(config, dict):
        raise ConfigError(f"Config file must contain a YAML mapping: {config_path}")

    return config
