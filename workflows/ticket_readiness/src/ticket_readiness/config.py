from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}

    if not isinstance(config, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {config_path}")

    return config
