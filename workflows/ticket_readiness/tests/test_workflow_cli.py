from __future__ import annotations

import json
from pathlib import Path

from ticket_readiness.approvals import write_approval_template
from ticket_readiness.artifacts import ArtifactStore
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


def test_run_analysis_rejects_absolute_artifact_root_before_writing(tmp_path, capsys):
    rejected_root = tmp_path / "absolute-artifact-root"
    config = _config(tmp_path, artifact_root=str(rejected_root))
    fixture = _fixture(tmp_path)

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

    assert exit_code == 1
    assert "artifact_root must be project-relative" in capsys.readouterr().out
    assert not rejected_root.exists()


def test_run_analysis_rejects_traversal_artifact_root_before_writing(tmp_path, capsys):
    config = _config(tmp_path, artifact_root="../sensitive")
    fixture = _fixture(tmp_path)

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

    assert exit_code == 1
    assert "artifact_root must not contain parent traversal" in capsys.readouterr().out
    assert not (tmp_path.parent / "sensitive").exists()


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


def test_post_approved_refuses_when_write_back_disabled(tmp_path, capsys):
    config = _config(tmp_path)
    run_id = _approved_run(tmp_path, issue_id="ASG-40")

    exit_code = main(["--config", str(config), "post-approved", "--run", run_id, "--issue-id", "ASG-40"])

    assert exit_code == 1
    assert "write-back is disabled" in capsys.readouterr().out


def test_post_approved_posts_when_write_back_enabled_and_approval_valid(tmp_path, capsys, monkeypatch):
    config = _config(tmp_path, write_back_enabled=True)
    run_id = _approved_run(tmp_path, issue_id="ASG-40")
    client = FakeCommentClient({"id": "comment-123"})
    monkeypatch.setattr("ticket_readiness.workflow.HTTPLinearCommentClient", lambda: client)

    exit_code = main(["--config", str(config), "post-approved", "--run", run_id, "--issue-id", "ASG-40"])

    assert exit_code == 0
    assert "Approved comment posted." in capsys.readouterr().out
    assert client.calls == [{"issue_id": "ASG-40", "body": "draft comment\n"}]


def _config(
    tmp_path: Path,
    *,
    artifact_root: str | None = None,
    write_back_enabled: bool = False,
) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(
        "\n".join(
            [
                "workspace: Asgard AI Agency",
                "team: Asgard AI Agency",
                "team_key: ASG",
                "artifact_root: " + (artifact_root or "runs"),
                "project:",
                "  name: AI Workflow Sandbox - Ticket Readiness",
                "  id: project-123",
                "  url: https://linear.app/asgard-ai-agency/project/project-123",
                "write_back:",
                f"  enabled: {str(write_back_enabled).lower()}",
                "  requires_human_approval: true",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _fixture(tmp_path: Path) -> Path:
    fixture = tmp_path / "issues.json"
    fixture.write_text(
        json.dumps([{"id": "ASG-40", "title": "Ticket", "description": "Acceptance Criteria: done"}]),
        encoding="utf-8",
    )
    return fixture


def _approved_run(tmp_path: Path, *, issue_id: str) -> str:
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )
    draft_relative_path = f"drafts/{issue_id}-linear-comment.md"
    run.path(draft_relative_path).write_text("draft comment\n", encoding="utf-8")
    template = write_approval_template(run=run, issue_id=issue_id, draft_relative_path=draft_relative_path)
    approval_path = run.path(template.path)
    payload = json.loads(approval_path.read_text(encoding="utf-8"))
    payload["decision"] = "approved"
    approval_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run.run_id


class FakeCommentClient:
    def __init__(self, response: dict):
        self._response = response
        self.calls: list[dict] = []

    def create_comment(self, *, issue_id: str, body: str) -> dict:
        self.calls.append({"issue_id": issue_id, "body": body})
        return self._response
