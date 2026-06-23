from __future__ import annotations

from ticket_readiness.artifacts import ArtifactStore
from ticket_readiness.reports import IssueReport
from ticket_readiness.summary import SummaryIssue, generate_run_summary


def test_generate_run_summary_groups_status_risk_and_links_artifacts(tmp_path):
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )
    issues = [
        SummaryIssue(
            issue_id="ASG-40",
            title="Ready-ish infrastructure ticket",
            readiness_status="needs_grooming",
            risk_level="medium",
            report=IssueReport(
                issue_id="ASG-40",
                markdown_path="reports/ASG-40-readiness.md",
                json_path="reports/ASG-40-readiness.json",
                readiness_status="needs_grooming",
                readiness_score=82,
                risk_level="medium",
            ),
            draft_path="drafts/ASG-40-linear-comment.md",
            writeback_status="skipped",
        ),
        SummaryIssue(
            issue_id="ASG-41",
            title="Vague production ticket",
            readiness_status="not_ready",
            risk_level="high",
            report=None,
            draft_path=None,
            writeback_status="not_attempted",
            error="LLM analysis failed.",
        ),
    ]

    summary_path = generate_run_summary(run=run, issues=issues)

    summary = run.path(summary_path).read_text(encoding="utf-8")
    assert "# Ticket Readiness Run Summary" in summary
    assert "needs_grooming: 1" in summary
    assert "not_ready: 1" in summary
    assert "medium: 1" in summary
    assert "high: 1" in summary
    assert "reports/ASG-40-readiness.md" in summary
    assert "drafts/ASG-40-linear-comment.md" in summary
    assert "LLM analysis failed." in summary
    assert "skipped" in summary


def test_generate_partial_run_summary_with_no_issues(tmp_path):
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )

    summary_path = generate_run_summary(run=run, issues=[], errors=["Linear read failed."])

    summary = run.path(summary_path).read_text(encoding="utf-8")
    assert "Total Issues: 0" in summary
    assert "Linear read failed." in summary
