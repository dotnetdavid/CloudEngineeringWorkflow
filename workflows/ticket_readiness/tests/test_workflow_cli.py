from __future__ import annotations

import json
from pathlib import Path

import pytest

from ticket_readiness.approvals import write_approval_template
from ticket_readiness.artifacts import ArtifactStore
from ticket_readiness.cli import main
from ticket_readiness.llm_analysis import LLMAnalysis, LLMAnalysisError


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


def test_run_analysis_emits_structured_logs_for_major_phases(tmp_path, capsys):
    config = _config(tmp_path)
    fixture = _fixture(tmp_path)

    exit_code = main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture), "--mock-llm"])

    assert exit_code == 0
    log_records = _json_stdout_records(capsys)
    run_id = next((tmp_path / "runs").iterdir()).name
    assert any(
        record["event_type"] == "run_completed"
        and record["severity"] == "info"
        and record["run_id"] == run_id
        for record in log_records
    )
    assert any(
        record["event_type"] == "issue_analyzed"
        and record["severity"] == "info"
        and record["run_id"] == run_id
        and record["issue_id"] == "ASG-40"
        for record in log_records
    )


def test_run_analysis_records_multi_issue_progress_and_preserves_summary_order(tmp_path, capsys):
    config = _config(tmp_path)
    fixture = tmp_path / "issues.json"
    fixture.write_text(
        json.dumps(
            [
                {"id": "ASG-40", "title": "First ticket", "description": "Acceptance Criteria: done"},
                {"id": "ASG-41", "title": "Second ticket", "description": "Acceptance Criteria: done"},
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture), "--mock-llm"])

    assert exit_code == 0
    run = next((tmp_path / "runs").iterdir())
    events = [
        json.loads(line)
        for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    progress_events = [event for event in events if event["event_type"] == "issue_progress"]
    assert [
        (event["issue_id"], event["state"], event["message"])
        for event in progress_events
    ] == [
        ("ASG-40", "running", "Processing issue 1 of 2."),
        ("ASG-41", "running", "Processing issue 2 of 2."),
    ]

    log_records = _json_stdout_records(capsys)
    assert any(
        record["event_type"] == "issue_progress"
        and record["issue_id"] == "ASG-41"
        and record["message"] == "Processing issue 2 of 2."
        for record in log_records
    )

    summary = (run / "summary.md").read_text(encoding="utf-8")
    assert summary.index("ASG-40 First ticket") < summary.index("ASG-41 Second ticket")


def test_run_analysis_loads_custom_readiness_checks_from_config(tmp_path):
    config = _config(
        tmp_path,
        extra_lines=[
            "readiness:",
            "  custom_checks:",
            "    - dimension: change_window",
            "      required: true",
            "      patterns:",
            "        - '\\bchange window\\b'",
            "        - '\\bmaintenance window\\b'",
            "      present_message: Change window signal is present.",
            "      missing_message: Change window is missing.",
        ],
    )
    fixture = tmp_path / "issues.json"
    fixture.write_text(
        json.dumps(
            [
                {
                    "id": "ASG-40",
                    "title": "Add S3 VPC endpoint",
                    "description": (
                        "Create a VPC endpoint in sandbox so that workers avoid NAT. "
                        "Acceptance Criteria: endpoint exists. Validation: verify S3 access. "
                        "Rollback: revert Terraform."
                    ),
                    "priority": {"value": 2, "name": "High"},
                    "estimate": 3,
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture), "--mock-llm"])

    assert exit_code == 0
    run = next((tmp_path / "runs").iterdir())
    report = json.loads((run / "reports" / "ASG-40-readiness.json").read_text(encoding="utf-8"))
    custom_finding = next(
        finding for finding in report["deterministic_findings"] if finding["dimension"] == "change_window"
    )
    assert custom_finding["status"] == "missing"
    assert custom_finding["required"] is True
    assert custom_finding["message"] == "Change window is missing."


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


def test_run_analysis_emits_structured_failure_log(tmp_path, capsys):
    rejected_root = tmp_path / "absolute-artifact-root"
    config = _config(tmp_path, artifact_root=str(rejected_root))
    fixture = _fixture(tmp_path)

    exit_code = main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture), "--mock-llm"])

    assert exit_code == 1
    log_records = _json_stdout_records(capsys)
    assert any(
        record["event_type"] == "run_analysis_failed"
        and record["severity"] == "error"
        and "artifact_root must be project-relative" in record["message"]
        for record in log_records
    )


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


def test_run_analysis_rejects_invalid_linear_project_id_before_writing(tmp_path, capsys):
    config = _config(tmp_path, project_id="project-123")
    fixture = _fixture(tmp_path)

    exit_code = main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture), "--mock-llm"])

    assert exit_code == 1
    assert "project.id must be a Linear project UUID" in capsys.readouterr().out
    assert not (tmp_path / "runs").exists()


def test_run_analysis_enforces_configured_max_issue_count(tmp_path, capsys):
    config = _config(tmp_path, max_issues=1)
    fixture = tmp_path / "issues.json"
    fixture.write_text(
        json.dumps(
            [
                {"id": "ASG-40", "title": "First ticket", "description": "Acceptance Criteria: done"},
                {"id": "ASG-41", "title": "Second ticket", "description": "Acceptance Criteria: done"},
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture), "--mock-llm"])

    assert exit_code == 1
    assert "exceeds configured max_issues" in capsys.readouterr().out
    run = next((tmp_path / "runs").iterdir())
    summary = (run / "summary.md").read_text(encoding="utf-8")
    assert "exceeds configured max_issues" in summary
    assert not (run / "inputs" / "issues" / "ASG-40.json").exists()


@pytest.mark.parametrize("issue_id", ["../ASG-40", "ASG/40", "asg-40", "ASG-abc"])
def test_run_analysis_rejects_invalid_fixture_issue_identifier_before_artifact_writes(
    tmp_path,
    capsys,
    issue_id,
):
    config = _config(tmp_path)
    fixture = tmp_path / "issues.json"
    fixture.write_text(
        json.dumps([{"id": issue_id, "title": "Unsafe ticket", "description": "Acceptance Criteria: done"}]),
        encoding="utf-8",
    )

    exit_code = main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture), "--mock-llm"])

    assert exit_code == 1
    assert "Invalid Linear issue identifier" in capsys.readouterr().out
    run = next((tmp_path / "runs").iterdir())
    assert not any((run / "inputs" / "issues").iterdir())


def test_run_analysis_records_openai_rate_limit_failures(tmp_path, monkeypatch):
    config = _config(tmp_path)
    fixture = _fixture(tmp_path)

    class RateLimitedOpenAIClient:
        def create_response(self, **kwargs):
            raise LLMAnalysisError("OpenAI response request was rate limited.")

    monkeypatch.setattr("ticket_readiness.workflow.HTTPOpenAIClient", lambda rate_limiter=None: RateLimitedOpenAIClient())

    exit_code = main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture)])

    assert exit_code == 0
    run = next((tmp_path / "runs").iterdir())
    events = (run / "events.jsonl").read_text(encoding="utf-8")
    summary = (run / "summary.md").read_text(encoding="utf-8")
    assert "issue_analysis_failed" in events
    assert "OpenAI response request was rate limited." in events
    assert "OpenAI response request was rate limited." in summary


def test_run_analysis_uses_configured_openai_model(tmp_path, monkeypatch):
    config = _config(tmp_path, extra_lines=["openai:", "  model: gpt-4.1-mini"])

    assert _run_with_recorded_model(config=config, tmp_path=tmp_path, monkeypatch=monkeypatch) == ["gpt-4.1-mini"]


def test_run_analysis_uses_openai_model_environment_override(tmp_path, monkeypatch):
    config = _config(tmp_path)
    monkeypatch.setenv("TICKET_READINESS_OPENAI_MODEL", "gpt-4.1")

    assert _run_with_recorded_model(config=config, tmp_path=tmp_path, monkeypatch=monkeypatch) == ["gpt-4.1"]


def test_run_analysis_prefers_configured_openai_model_over_environment(tmp_path, monkeypatch):
    config = _config(tmp_path, extra_lines=["openai:", "  model: gpt-4.1-mini"])
    monkeypatch.setenv("TICKET_READINESS_OPENAI_MODEL", "gpt-4.1")

    assert _run_with_recorded_model(config=config, tmp_path=tmp_path, monkeypatch=monkeypatch) == ["gpt-4.1-mini"]


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


def test_summarize_run_reconstructs_existing_issue_artifacts(tmp_path):
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
    assert main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture), "--mock-llm"]) == 0
    run = next((tmp_path / "runs").iterdir())
    (run / "summary.md").write_text("stale empty summary\n", encoding="utf-8")

    exit_code = main(["--config", str(config), "summarize-run", "--run", run.name])

    assert exit_code == 0
    summary = (run / "summary.md").read_text(encoding="utf-8")
    assert "Total Issues: 1" in summary
    assert "ASG-40 Add S3 VPC endpoint for private artifact bucket access" in summary
    assert "reports/ASG-40-readiness.md" in summary
    assert "drafts/ASG-40-linear-comment.md" in summary
    assert "not_attempted" in summary


def test_summarize_run_preserves_issue_errors_from_events(tmp_path):
    config = _config(tmp_path)
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )
    run.write_json(
        "inputs/issues/ASG-41.json",
        {"identifier": "ASG-41", "title": "Vague production ticket"},
    )
    run.append_event(
        event_type="issue_analysis_failed",
        state="failed",
        issue_id="ASG-41",
        message="LLM analysis failed.",
    )

    exit_code = main(["--config", str(config), "summarize-run", "--run", run.run_id])

    assert exit_code == 0
    summary = run.path("summary.md").read_text(encoding="utf-8")
    assert "Total Issues: 1" in summary
    assert "ASG-41 Vague production ticket" in summary
    assert "analysis_failed" in summary
    assert "LLM analysis failed." in summary


def test_summarize_run_ignores_approval_validation_failures_as_issue_errors(tmp_path):
    config = _config(tmp_path)
    fixture = _fixture(tmp_path)
    assert main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture), "--mock-llm"]) == 0
    run = next((tmp_path / "runs").iterdir())
    events_path = run / "events.jsonl"
    with events_path.open("a", encoding="utf-8") as events:
        events.write(
            json.dumps(
                {
                    "event_type": "approval_validation_failed",
                    "issue_id": "ASG-40",
                    "message": "Approval record is not approved.",
                    "run_id": run.name,
                    "state": "failed",
                    "timestamp": "2026-06-24T00:00:00Z",
                },
                sort_keys=True,
            )
            + "\n"
        )

    exit_code = main(["--config", str(config), "summarize-run", "--run", run.name])

    assert exit_code == 0
    summary = (run / "summary.md").read_text(encoding="utf-8")
    assert "Total Issues: 1" in summary
    assert "ASG-40 Ticket" in summary
    assert "Approval record is not approved." not in summary
    assert "analysis_failed" not in summary


def test_summarize_run_returns_nonzero_for_missing_run(tmp_path, capsys):
    config = _config(tmp_path)

    exit_code = main(["--config", str(config), "summarize-run", "--run", "missing-run"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "missing-run" in captured.out
    log_records = _json_stdout_records_from_text(captured.out, captured.err)
    assert any(
        record["event_type"] == "command_failed"
        and record["severity"] == "error"
        and "missing-run" in record["message"]
        for record in log_records
    )


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
    project_id: str = "8ff212c4-dfc7-4152-88e0-3dd65723a420",
    max_issues: int | None = None,
    write_back_enabled: bool = False,
    extra_lines: list[str] | None = None,
) -> Path:
    lines = [
        "workspace: Asgard AI Agency",
        "team: Asgard AI Agency",
        "team_key: ASG",
        "artifact_root: " + (artifact_root or "runs"),
    ]
    if max_issues is not None:
        lines.append(f"max_issues: {max_issues}")
    lines.extend(
        [
            "project:",
            "  name: AI Workflow Sandbox - Ticket Readiness",
            f"  id: {project_id}",
            f"  url: https://linear.app/asgard-ai-agency/project/{project_id}",
            "write_back:",
            f"  enabled: {str(write_back_enabled).lower()}",
            "  requires_human_approval: true",
        ]
    )
    if extra_lines:
        lines.extend(extra_lines)
    path = tmp_path / "config.yaml"
    path.write_text("\n".join(lines), encoding="utf-8")
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
    payload["approved_by"] = "Dave"
    payload["approved_at"] = "2026-06-24T18:00:00Z"
    approval_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run.run_id


class FakeCommentClient:
    def __init__(self, response: dict):
        self._response = response
        self.calls: list[dict] = []

    def create_comment(self, *, issue_id: str, body: str) -> dict:
        self.calls.append({"issue_id": issue_id, "body": body})
        return self._response


def _run_with_recorded_model(*, config: Path, tmp_path: Path, monkeypatch) -> list[str]:
    fixture = _fixture(tmp_path)
    models = []

    class RecordingAdapter:
        def __init__(self, client, model):
            models.append(model)

        def analyze(self, *, issue, rubric, deterministic_result):
            return _analysis()

    monkeypatch.setattr("ticket_readiness.workflow.HTTPOpenAIClient", lambda rate_limiter=None: object())
    monkeypatch.setattr("ticket_readiness.workflow.LLMAnalysisAdapter", RecordingAdapter)

    assert main(["--config", str(config), "run-analysis", "--fixture-data", str(fixture)]) == 0
    return models


def _analysis() -> LLMAnalysis:
    return LLMAnalysis(
        summary="Ticket is ready enough for test analysis.",
        work_type="infrastructure_change",
        risk_level="low",
        readiness_status="ready",
        missing_information=(),
        grooming_questions=(),
        operational_risk=(),
        security_notes=(),
        acceptance_criteria_improvements=(),
        recommended_next_action="Proceed with normal review.",
        draft_comment="Ticket readiness looks acceptable.",
    )


def _json_stdout_records(capsys):
    captured = capsys.readouterr()
    return _json_stdout_records_from_text(captured.out, captured.err)


def _json_stdout_records_from_text(stdout: str, stderr: str):
    return [
        json.loads(line)
        for line in (stdout + "\n" + stderr).splitlines()
        if line.startswith("{")
    ]
