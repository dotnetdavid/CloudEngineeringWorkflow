from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ticket_readiness.approvals import ApprovalError, validate_approval_record, write_approval_template
from ticket_readiness.artifacts import ArtifactStore, RunArtifacts
from ticket_readiness.config import load_config
from ticket_readiness.drafts import generate_draft_comment
from ticket_readiness.errors import TicketReadinessError
from ticket_readiness.linear import LinearGraphQLClient, LinearIssue, LinearIssueReader, normalize_issue
from ticket_readiness.llm_analysis import (
    HTTPOpenAIClient,
    LLMAnalysisAdapter,
    validate_model_output,
)
from ticket_readiness.rate_limit import FixedDelayRateLimiter
from ticket_readiness.readiness import (
    DeterministicReadinessResult,
    ReadinessConfigError,
    evaluate_issue,
    load_custom_checks,
)
from ticket_readiness.reports import IssueReport, generate_issue_report
from ticket_readiness.summary import SummaryIssue, generate_run_summary
from ticket_readiness.writeback import HTTPLinearCommentClient, LinearCommentWriteBack, WriteBackError


class WorkflowError(TicketReadinessError):
    """Raised when the workflow cannot complete."""


_LINEAR_PROJECT_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def run_analysis(
    *,
    config_path: Path,
    fixture_data: Path | None = None,
    mock_llm: bool = False,
) -> str:
    config = load_config(config_path)
    _linear_project_id(config)
    run = _create_run(config, config_path=config_path)
    run.append_event(event_type="run_started", state="running", message="Run started.")

    rate_limiter = _api_rate_limiter(config)
    try:
        issues = (
            _load_fixture_issues(fixture_data, config=config)
            if fixture_data
            else _read_linear_issues(config, rate_limiter=rate_limiter)
        )
    except Exception as exc:
        message = str(exc)
        run.append_event(event_type="issue_load_failed", state="failed", message=message)
        generate_run_summary(run=run, issues=[], errors=[message])
        raise WorkflowError(message) from exc

    run.write_json("inputs/linear-project.json", config.get("project", {}))

    summary_issues: list[SummaryIssue] = []
    errors: list[str] = []
    rubric = _default_rubric()
    try:
        custom_checks = load_custom_checks(config)
    except ReadinessConfigError as exc:
        message = str(exc)
        run.append_event(event_type="readiness_config_failed", state="failed", message=message)
        generate_run_summary(run=run, issues=[], errors=[message])
        raise WorkflowError(message) from exc

    total_issues = len(issues)
    for index, issue in enumerate(issues, start=1):
        run.append_event(
            event_type="issue_progress",
            state="running",
            issue_id=issue.identifier,
            message=f"Processing issue {index} of {total_issues}.",
        )
        try:
            run.write_json(f"inputs/issues/{issue.identifier}.json", issue.to_dict())
            deterministic = evaluate_issue(issue, custom_checks=custom_checks)
            analysis = (
                _mock_analysis(issue, deterministic)
                if mock_llm
                else _live_analysis(issue, rubric, deterministic, rate_limiter=rate_limiter)
            )
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
    run = _existing_run(load_config(config_path), run_id, config_path=config_path)
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
    if not _write_back_enabled(config):
        raise WorkflowError("Linear write-back is disabled by config: write_back.enabled must be true.")
    run = _existing_run(config, run_id, config_path=config_path)
    draft_relative_path = f"drafts/{issue_id}-linear-comment.md"
    writer = LinearCommentWriteBack(client=HTTPLinearCommentClient())
    try:
        writer.post_approved(run=run, issue_id=issue_id, draft_relative_path=draft_relative_path)
    except WriteBackError:
        return False
    return True


def summarize_run(*, config_path: Path, run_id: str) -> str:
    run = _existing_run(load_config(config_path), run_id, config_path=config_path)
    issues, errors = _reconstruct_summary_state(run)
    return generate_run_summary(run=run, issues=issues, errors=errors)


def _create_run(config: dict[str, Any], *, config_path: Path) -> RunArtifacts:
    project = config["project"]
    root = _artifact_root(config, config_path=config_path)
    return ArtifactStore(root).create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source=str(config.get("team_key") or config.get("team") or "linear-sandbox"),
        linear_project_id=_linear_project_id(config),
        linear_project_url=str(project.get("url") or ""),
    )


def _existing_run(config: dict[str, Any], run_id: str, *, config_path: Path) -> RunArtifacts:
    root = _artifact_root(config, config_path=config_path) / run_id
    return RunArtifacts(run_id=run_id, root=root)


def _artifact_root(config: dict[str, Any], *, config_path: Path) -> Path:
    configured_root = Path(str(config.get("artifact_root", "runs")))
    if configured_root.is_absolute():
        raise WorkflowError("artifact_root must be project-relative, not absolute.")
    if ".." in configured_root.parts:
        raise WorkflowError("artifact_root must not contain parent traversal ('..').")
    return config_path.parent / configured_root


def _linear_project_id(config: dict[str, Any]) -> str:
    project = config.get("project")
    if not isinstance(project, dict):
        raise WorkflowError("project must be a configuration mapping with a Linear project UUID in project.id.")

    project_id = str(project.get("id") or "").strip()
    if not _LINEAR_PROJECT_UUID_PATTERN.match(project_id):
        raise WorkflowError("project.id must be a Linear project UUID.")

    return project_id


def _write_back_enabled(config: dict[str, Any]) -> bool:
    write_back = config.get("write_back")
    return isinstance(write_back, dict) and write_back.get("enabled") is True


def _reconstruct_summary_state(run: RunArtifacts) -> tuple[list[SummaryIssue], list[str]]:
    snapshots = _issue_snapshots(run)
    issue_errors, run_errors = _errors_from_events(run)
    summary_issues: dict[str, SummaryIssue] = {}

    for report_path in sorted(run.path("reports").glob("*-readiness.json")):
        payload = _read_json_file(report_path)
        issue_id = str(payload.get("issue_id") or report_path.name.removesuffix("-readiness.json"))
        issue_snapshot = snapshots.get(issue_id, {})
        draft_path = _draft_path(run, issue_id, payload)
        summary_issues[issue_id] = SummaryIssue(
            issue_id=issue_id,
            title=str(payload.get("issue_title") or issue_snapshot.get("title") or ""),
            readiness_status=str(payload.get("readiness_status") or "unknown"),
            risk_level=str(payload.get("risk_level") or "unknown"),
            report=IssueReport(
                issue_id=issue_id,
                markdown_path=f"reports/{report_path.name.removesuffix('.json')}.md",
                json_path=_relative_to_run(run, report_path),
                readiness_status=str(payload.get("readiness_status") or "unknown"),
                readiness_score=int(payload.get("readiness_score") or 0),
                risk_level=str(payload.get("risk_level") or "unknown"),
            ),
            draft_path=draft_path,
            writeback_status=_writeback_status(run, issue_id),
            error=issue_errors.get(issue_id),
        )

    for issue_id, error in issue_errors.items():
        if issue_id in summary_issues:
            continue
        issue_snapshot = snapshots.get(issue_id, {})
        summary_issues[issue_id] = SummaryIssue(
            issue_id=issue_id,
            title=str(issue_snapshot.get("title") or ""),
            readiness_status="analysis_failed",
            risk_level="unknown",
            report=None,
            draft_path=_draft_path(run, issue_id, {}),
            writeback_status=_writeback_status(run, issue_id),
            error=error,
        )

    return [summary_issues[key] for key in sorted(summary_issues)], run_errors


def _issue_snapshots(run: RunArtifacts) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for issue_path in sorted(run.path("inputs", "issues").glob("*.json")):
        payload = _read_json_file(issue_path)
        issue_id = str(payload.get("identifier") or payload.get("id") or issue_path.stem)
        snapshots[issue_id] = payload
    return snapshots


def _errors_from_events(run: RunArtifacts) -> tuple[dict[str, str], list[str]]:
    issue_errors: dict[str, str] = {}
    run_errors: list[str] = []
    events_path = run.path("events.jsonl")
    if not events_path.exists():
        return issue_errors, run_errors

    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            run_errors.append("Malformed event record found in events.jsonl.")
            continue
        if event.get("state") != "failed":
            continue
        message = str(event.get("message") or "Unknown failure.")
        issue_id = event.get("issue_id")
        if issue_id:
            if event.get("event_type") == "issue_analysis_failed":
                issue_errors[str(issue_id)] = message
        else:
            run_errors.append(message)
    return issue_errors, run_errors


def _draft_path(run: RunArtifacts, issue_id: str, report_payload: dict[str, Any]) -> str | None:
    draft_from_report = report_payload.get("draft_comment_path")
    if draft_from_report:
        return str(draft_from_report)
    draft_path = run.path("drafts", f"{issue_id}-linear-comment.md")
    if draft_path.exists():
        return _relative_to_run(run, draft_path)
    return None


def _writeback_status(run: RunArtifacts, issue_id: str) -> str:
    approval_path = run.path("approvals", f"{issue_id}-approval.json")
    if not approval_path.exists():
        return "not_attempted"
    approval = _read_json_file(approval_path)
    if approval.get("posted_comment_id"):
        return "posted"
    return "not_attempted"


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"Failed to read run artifact JSON: {path.name}") from exc
    if not isinstance(payload, dict):
        raise WorkflowError(f"Run artifact JSON must contain an object: {path.name}")
    return payload


def _relative_to_run(run: RunArtifacts, path: Path) -> str:
    return path.relative_to(run.root).as_posix()


def _load_fixture_issues(path: Path | None, *, config: dict[str, Any]) -> list[LinearIssue]:
    if path is None:
        raise WorkflowError("fixture_data is required in fixture mode.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise WorkflowError("Fixture data must be a JSON array of issues.")
    _enforce_max_issues(len(payload), config=config)
    return [normalize_issue(item) for item in payload]


def _read_linear_issues(config: dict[str, Any], *, rate_limiter: FixedDelayRateLimiter) -> list[LinearIssue]:
    project_id = _linear_project_id(config)
    return LinearIssueReader(
        client=LinearGraphQLClient(rate_limiter=rate_limiter)
    ).read_project_issues(project_id, max_issues=_max_issues(config))


def _live_analysis(
    issue: LinearIssue,
    rubric: dict[str, Any],
    deterministic: DeterministicReadinessResult,
    *,
    rate_limiter: FixedDelayRateLimiter,
):
    return LLMAnalysisAdapter(client=HTTPOpenAIClient(rate_limiter=rate_limiter)).analyze(
        issue=issue,
        rubric=rubric,
        deterministic_result=deterministic,
    )


def _api_rate_limiter(config: dict[str, Any]) -> FixedDelayRateLimiter:
    rate_limit = config.get("api_rate_limit")
    delay_seconds = 0.0
    if isinstance(rate_limit, dict):
        delay_seconds = float(rate_limit.get("min_interval_seconds") or 0)
    return FixedDelayRateLimiter(delay_seconds=delay_seconds)


def _max_issues(config: dict[str, Any]) -> int | None:
    value = config.get("max_issues")
    if value is None:
        return None
    try:
        max_issues = int(value)
    except (TypeError, ValueError) as exc:
        raise WorkflowError("max_issues must be a positive integer.") from exc
    if max_issues < 1:
        raise WorkflowError("max_issues must be a positive integer.")
    return max_issues


def _enforce_max_issues(issue_count: int, *, config: dict[str, Any]) -> None:
    max_issues = _max_issues(config)
    if max_issues is not None and issue_count > max_issues:
        raise WorkflowError(
            f"Run issue count {issue_count} exceeds configured max_issues: {max_issues}"
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
