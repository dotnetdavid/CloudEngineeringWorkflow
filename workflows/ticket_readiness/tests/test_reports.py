from __future__ import annotations

import json

import pytest

from ticket_readiness.artifacts import ArtifactStore
from ticket_readiness.linear import LinearIssue, LinearPriority
from ticket_readiness.llm_analysis import validate_model_output
from ticket_readiness.readiness import evaluate_issue
from ticket_readiness.reports import ReportGenerationError, generate_issue_report


def test_generate_issue_report_writes_markdown_and_json(tmp_path):
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )
    issue = _issue()
    deterministic = evaluate_issue(issue)
    llm = validate_model_output(_llm_output())

    report = generate_issue_report(
        run=run,
        issue=issue,
        deterministic_result=deterministic,
        llm_analysis=llm,
        draft_comment_path="drafts/ASG-40-linear-comment.md",
    )

    assert report.issue_id == "ASG-40"
    assert report.markdown_path == "reports/ASG-40-readiness.md"
    assert report.json_path == "reports/ASG-40-readiness.json"

    markdown = run.path(report.markdown_path).read_text(encoding="utf-8")
    assert "# ASG-40: Add S3 VPC endpoint for private artifact bucket access" in markdown
    assert "Readiness: `needs_grooming`" in markdown
    assert "Draft Comment: `drafts/ASG-40-linear-comment.md`" in markdown
    assert "## Deterministic Findings" in markdown
    assert "## Security Notes" in markdown

    payload = json.loads(run.path(report.json_path).read_text(encoding="utf-8"))
    assert payload["issue_id"] == "ASG-40"
    assert payload["issue_url"] == issue.url
    assert payload["readiness_status"] == "needs_grooming"
    assert isinstance(payload["readiness_score"], int)
    assert "acceptance_criteria" in payload["dimension_scores"]
    assert payload["draft_comment_path"] == "drafts/ASG-40-linear-comment.md"
    assert payload["model_metadata"] == {}


def test_report_generation_failure_fails_closed(tmp_path):
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )
    issue = _issue()
    llm = validate_model_output(_llm_output())

    reports_dir = run.path("reports")
    reports_dir.rmdir()
    reports_dir.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ReportGenerationError):
        generate_issue_report(
            run=run,
            issue=issue,
            deterministic_result=evaluate_issue(issue),
            llm_analysis=llm,
            draft_comment_path="drafts/ASG-40-linear-comment.md",
        )


def _issue() -> LinearIssue:
    return LinearIssue(
        identifier="ASG-40",
        title="Add S3 VPC endpoint for private artifact bucket access",
        description=(
            "Create a VPC endpoint so that private workers can reach S3. "
            "Acceptance Criteria: endpoint exists. Validation: verify S3 access. "
            "Rollback: revert Terraform. Security: no public ingress."
        ),
        priority=LinearPriority(value=2, name="High"),
        estimate=3,
        url="https://linear.app/asgard-ai-agency/issue/ASG-40/example",
    )


def _llm_output():
    return {
        "summary": "Ticket is close but needs route table ownership clarified.",
        "work_type": "infrastructure_change",
        "risk_level": "medium",
        "readiness_status": "needs_grooming",
        "missing_information": ["Owner is not explicit."],
        "grooming_questions": ["Who owns the route table update?"],
        "operational_risk": ["Route table changes can affect private subnet egress."],
        "security_notes": ["No public ingress is requested."],
        "acceptance_criteria_improvements": ["Name the target route tables."],
        "recommended_next_action": "Clarify owner and route table scope before sprint commitment.",
        "draft_comment": "Please clarify the owner and target route tables.",
    }
