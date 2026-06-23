from pathlib import Path

from ticket_readiness.config import load_config


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

