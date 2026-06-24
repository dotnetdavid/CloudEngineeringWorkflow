from pathlib import Path

import pytest

from ticket_readiness.config import ConfigError, load_config


def test_load_config_reads_yaml_file(tmp_path: Path):
    config_path = tmp_path / "linear-sandbox.yaml"
    config_path.write_text(
        "\n".join(
            [
                "workspace: Asgard AI Agency",
                "team: Asgard AI Agency",
                "project:",
                "  id: 8ff212c4-dfc7-4152-88e0-3dd65723a420",
                "write_back:",
                "  enabled: false",
                "  requires_human_approval: true",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config["workspace"] == "Asgard AI Agency"
    assert config["project"]["id"] == "8ff212c4-dfc7-4152-88e0-3dd65723a420"
    assert config["write_back"]["requires_human_approval"] is True


def test_load_config_rejects_non_mapping_yaml_with_domain_error(tmp_path: Path):
    config_path = tmp_path / "linear-sandbox.yaml"
    config_path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Config file must contain a YAML mapping"):
        load_config(config_path)
