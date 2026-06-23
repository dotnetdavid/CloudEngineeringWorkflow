from __future__ import annotations

import json
from pathlib import Path

from ticket_readiness.cli import main


def test_run_analysis_fixture_mode_creates_artifacts(tmp_path):
    config = _config(tmp_path)
    fixture = tmp_path / "issues.json"
    fixture.write_text(
        json.dumps(
            [
                {
                    "id": "ASG-40",
                    "title": "Add S3 VPC endpoint for private artifact bucket access",
                    "description": (
                        "Create a VPC endpoint so that private workers can reach S3. "
                        "Acceptance Criteria: endpoint exists. Validation: verify S3 access. "
                        "Rollback: revert Terraform. Security: no public ingress."
                    ),
                    "priority": {"value": 2, "name": "High"},
                    "estimate": 3,
                    "url": "https://linear.app/asgard-ai-agency/issue/ASG-40/example",
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--config",
            str(config),
            "run-analysis",
            "--fixture-data",
            str(fixture),
            "--mock-llm",
        ]
    )

    assert exit_code == 0
    run_dirs = list((tmp_path / "runs").iterdir())
    assert len(run_dirs) == 1
    run = run_dirs[0]
    assert (run / "manifest.json").exists()
    assert (run / "events.jsonl").exists()
    assert (run / "inputs" / "issues" / "ASG-40.json").exists()
    assert (run / "reports" / "ASG-40-readiness.md").exists()
    assert (run / "drafts" / "ASG-40-linear-comment.md").exists()
    assert (run / "approvals" / "ASG-40-approval.json").exists()
    assert (run / "summary.md").exists()


def test_validate_approvals_command_blocks_default_skipped_template(tmp_path):
    config = _config(tmp_path)
    fixture = tmp_path / "issues.json"
    fixture.write_text(
        json.dumps([{"id": "ASG-40", "title": "Ticket", "description": "Acceptance Criteria: done"}]),
        encoding="utf-8",
    )
    assert main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture), "--mock-llm"]) == 0
    run_id = next((tmp_path / "runs").iterdir()).name

    exit_code = main(["--config", str(config), "validate-approvals", "--run", run_id])

    assert exit_code == 1


def _config(tmp_path: Path) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(
        "\n".join(
            [
                "workspace: Asgard AI Agency",
                "team: Asgard AI Agency",
                "team_key: ASG",
                "artifact_root: " + str(tmp_path / "runs"),
                "project:",
                "  name: AI Workflow Sandbox - Ticket Readiness",
                "  id: project-123",
                "  url: https://linear.app/asgard-ai-agency/project/project-123",
                "write_back:",
                "  enabled: false",
                "  requires_human_approval: true",
            ]
        ),
        encoding="utf-8",
    )
    return path
