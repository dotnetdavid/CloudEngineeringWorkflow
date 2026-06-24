from __future__ import annotations

import json

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


def test_generate_run_summary_records_workflow_metrics_in_summary_and_manifest(tmp_path):
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )
    run.append_event(event_type="run_started", state="running", message="Run started.")
    run.append_event(
        event_type="issue_analyzed",
        state="succeeded",
        issue_id="ASG-40",
        message="Issue analysis artifacts written.",
    )
    run.append_event(
        event_type="issue_analysis_failed",
        state="failed",
        issue_id="ASG-41",
        message="OpenAI response request was rate limited.",
    )
    run.write_json(
        "reports/ASG-40-readiness.json",
        {
            "issue_id": "ASG-40",
            "readiness_status": "ready",
            "risk_level": "low",
            "model_metadata": {
                "model": "gpt-5-mini",
                "latency_ms": 812,
                "usage": {"input_tokens": 100, "output_tokens": 40, "total_tokens": 140},
            },
        },
    )
    issues = [
        SummaryIssue(
            issue_id="ASG-40",
            title="Ready infrastructure ticket",
            readiness_status="ready",
            risk_level="low",
            report=IssueReport(
                issue_id="ASG-40",
                markdown_path="reports/ASG-40-readiness.md",
                json_path="reports/ASG-40-readiness.json",
                readiness_status="ready",
                readiness_score=100,
                risk_level="low",
            ),
            draft_path="drafts/ASG-40-linear-comment.md",
            writeback_status="not_attempted",
        ),
        SummaryIssue(
            issue_id="ASG-41",
            title="Rate limited ticket",
            readiness_status="analysis_failed",
            risk_level="unknown",
            report=None,
            draft_path=None,
            writeback_status="not_attempted",
            error="OpenAI response request was rate limited.",
        ),
    ]

    summary_path = generate_run_summary(run=run, issues=issues, errors=["OpenAI API hiccup."])

    summary = run.path(summary_path).read_text(encoding="utf-8")
    assert "## Workflow Metrics" in summary
    assert "Issues processed: 2" in summary
    assert "Issue analysis succeeded: 1" in summary
    assert "Issue analysis failed: 1" in summary
    assert "Known OpenAI response calls: 1" in summary
    assert "Model usage total tokens: 140" in summary
    assert "Model latency samples: 1" in summary

    manifest = json.loads(run.path("manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["issues_processed"] == 2
    assert manifest["counts"]["issue_analysis"]["succeeded"] == 1
    assert manifest["counts"]["issue_analysis"]["failed"] == 1
    assert manifest["counts"]["api_calls"]["openai_responses"]["known"] == 1
    assert manifest["counts"]["model_usage"]["total_tokens"] == 140
    assert manifest["counts"]["model_latency"]["samples"] == 1
    assert manifest["errors"] == ["OpenAI API hiccup.", "ASG-41: OpenAI response request was rate limited."]
