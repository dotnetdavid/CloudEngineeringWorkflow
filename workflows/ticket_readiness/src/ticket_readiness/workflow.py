from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ticket_readiness.approvals import ApprovalError, validate_approval_record, write_approval_template
from ticket_readiness.artifacts import ArtifactStore, RunArtifacts
from ticket_readiness.config import load_config
from ticket_readiness.drafts import generate_draft_comment
from ticket_readiness.linear import LinearGraphQLClient, LinearIssue, LinearIssueReader, normalize_issue
from ticket_readiness.llm_analysis import (
    HTTPOpenAIClient,
    LLMAnalysisAdapter,
    validate_model_output,
)
from ticket_readiness.readiness import DeterministicReadinessResult, evaluate_issue
from ticket_readiness.reports import IssueReport, generate_issue_report
from ticket_readiness.summary import SummaryIssue, generate_run_summary
from ticket_readiness.writeback import HTTPLinearCommentClient, LinearCommentWriteBack, WriteBackError


class WorkflowError(RuntimeError):
    """Raised when the workflow cannot complete."""


def run_analysis(
    *,
    config_path: Path,
    fixture_data: Path | None = None,
    mock_llm: bool = False,
) -> str:
    config = load_config(config_path)
    run = _create_run(config)
    run.append_event(event_type="run_started", state="running", message="Run started.")

    issues = _load_fixture_issues(fixture_data) if fixture_data else _read_linear_issues(config)
    run.write_json("inputs/linear-project.json", config.get("project", {}))

    summary_issues: list[SummaryIssue] = []
    errors: list[str] = []
    rubric = _default_rubric()

    for issue in issues:
        try:
            run.write_json(f"inputs/issues/{issue.identifier}.json", issue.to_dict())
            deterministic = evaluate_issue(issue)
            analysis = _mock_analysis(issue, deterministic) if mock_llm else _live_analysis(issue, rubric, deterministic)
            draft = generate_draft_comment(run=run, issue=issue, llm_analysis=analysis)
            report = generate_issue_report(
                run=run,
                issue=issue,
                deterministic_result=deterministic,
                llm_analysis=analysis,
                draft_comment_path=draft.path,
            )
            write_approval_template(run=run, issue_id=issue.identifier, draft_relative_path=draft.path)
            summary_issues.append(
                SummaryIssue(
                    issue_id=issue.identifier,
                    title=issue.title,
                    readiness_status=analysis.readiness_status,
                    risk_level=analysis.risk_level,
                    report=report,
                    draft_path=draft.path,
                    writeback_status="not_attempted",
                )
            )
            run.append_event(
                event_type="issue_analyzed",
                state="succeeded",
                issue_id=issue.identifier,
                message="Issue analysis artifacts written.",
            )
        except Exception as exc:
            errors.append(f"{issue.identifier}: {exc}")
            summary_issues.append(
                SummaryIssue(
                    issue_id=issue.identifier,
                    title=issue.title,
                    readiness_status="analysis_failed",
                    risk_level="unknown",
                    report=None,
                    draft_path=None,
                    writeback_status="not_attempted",
                    error=str(exc),
                )
            )
            run.append_event(
                event_type="issue_analysis_failed",
                state="failed",
                issue_id=issue.identifier,
                message=str(exc),
            )

    generate_run_summary(run=run, issues=summary_issues, errors=errors)
    run.append_event(event_type="run_completed", state="succeeded", message="Run completed.")
    return run.run_id


def validate_approvals(*, config_path: Path, run_id: str) -> bool:
    run = _existing_run(load_config(config_path), run_id)
    drafts = sorted(run.path("drafts").glob("*-linear-comment.md"))
    all_valid = True
    for draft in drafts:
        issue_id = draft.name.removesuffix("-linear-comment.md")
        relative = f"drafts/{draft.name}"
        try:
            validate_approval_record(run=run, issue_id=issue_id, draft_relative_path=relative)
            run.append_event(
                event_type="approval_validated",
                state="succeeded",
                issue_id=issue_id,
                message="Approval is valid.",
            )
        except ApprovalError as exc:
            all_valid = False
            run.append_event(
                event_type="approval_validation_failed",
                state="failed",
                issue_id=issue_id,
                message=str(exc),
            )
    return all_valid


def post_approved(*, config_path: Path, run_id: str, issue_id: str) -> bool:
    config = load_config(config_path)
    run = _existing_run(config, run_id)
    draft_relative_path = f"drafts/{issue_id}-linear-comment.md"
    writer = LinearCommentWriteBack(client=HTTPLinearCommentClient())
    try:
        writer.post_approved(run=run, issue_id=issue_id, draft_relative_path=draft_relative_path)
    except WriteBackError:
        return False
    return True


def summarize_run(*, config_path: Path, run_id: str) -> str:
    run = _existing_run(load_config(config_path), run_id)
    # Regenerating from rich state arrives in a later dashboard-worthy pass; for now
    # preserve partial-run behavior and ensure summary.md exists.
    return generate_run_summary(run=run, issues=[], errors=[])


def _create_run(config: dict[str, Any]) -> RunArtifacts:
    project = config["project"]
    root = Path(config.get("artifact_root", "runs"))
    return ArtifactStore(root).create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source=str(config.get("team_key") or config.get("team") or "linear-sandbox"),
        linear_project_id=str(project["id"]),
        linear_project_url=str(project.get("url") or ""),
    )


def _existing_run(config: dict[str, Any], run_id: str) -> RunArtifacts:
    root = Path(config.get("artifact_root", "runs")) / run_id
    return RunArtifacts(run_id=run_id, root=root)


def _load_fixture_issues(path: Path | None) -> list[LinearIssue]:
    if path is None:
        raise WorkflowError("fixture_data is required in fixture mode.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise WorkflowError("Fixture data must be a JSON array of issues.")
    return [normalize_issue(item) for item in payload]


def _read_linear_issues(config: dict[str, Any]) -> list[LinearIssue]:
    project_id = str(config["project"]["id"])
    return LinearIssueReader(client=LinearGraphQLClient()).read_project_issues(project_id)


def _live_analysis(
    issue: LinearIssue,
    rubric: dict[str, Any],
    deterministic: DeterministicReadinessResult,
):
    return LLMAnalysisAdapter(client=HTTPOpenAIClient()).analyze(
        issue=issue,
        rubric=rubric,
        deterministic_result=deterministic,
    )


def _mock_analysis(issue: LinearIssue, deterministic: DeterministicReadinessResult):
    missing = [
        finding.message
        for finding in deterministic.findings
        if finding.status == "missing" and finding.required
    ]
    risk_level = _highest_risk(deterministic)
    readiness = "needs_grooming" if missing else "ready"
    if deterministic.trivially_incomplete:
        readiness = "not_ready"
    return validate_model_output(
        {
            "summary": f"{issue.identifier} evaluated in fixture mode.",
            "work_type": deterministic.work_type,
            "risk_level": risk_level,
            "readiness_status": readiness,
            "missing_information": missing,
            "grooming_questions": [f"What remaining context is needed for {issue.identifier}?"],
            "operational_risk": [flag.message for flag in deterministic.risk_flags],
            "security_notes": ["Review security impact before approving write-back."],
            "acceptance_criteria_improvements": ["Make acceptance criteria explicit and testable."],
            "recommended_next_action": "Review generated findings and update the ticket before sprint commitment.",
            "draft_comment": (
                f"Ticket readiness review for {issue.identifier}: {readiness}. "
                "Please review missing information and grooming questions before sprint commitment."
            ),
        }
    )


def _highest_risk(deterministic: DeterministicReadinessResult) -> str:
    levels = {flag.level for flag in deterministic.risk_flags}
    if "high" in levels:
        return "high"
    if "medium" in levels:
        return "medium"
    return "low"


def _default_rubric() -> dict[str, Any]:
    return {
        "statuses": {
            "ready": {},
            "needs_grooming": {},
            "blocked": {},
            "not_ready": {},
        }
    }
