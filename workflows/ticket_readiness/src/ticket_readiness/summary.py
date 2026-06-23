from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ticket_readiness.artifacts import ArtifactWriteError, RunArtifacts
from ticket_readiness.reports import IssueReport


class SummaryGenerationError(RuntimeError):
    """Raised when the run summary cannot be written."""


@dataclass(frozen=True)
class SummaryIssue:
    issue_id: str
    title: str
    readiness_status: str
    risk_level: str
    report: IssueReport | None
    draft_path: str | None
    writeback_status: str
    error: str | None = None


def generate_run_summary(
    *,
    run: RunArtifacts,
    issues: list[SummaryIssue],
    errors: list[str] | None = None,
) -> str:
    summary_path = "summary.md"
    content = render_run_summary(run=run, issues=issues, errors=errors or [])
    try:
        run.path(summary_path).write_text(content, encoding="utf-8")
    except (ArtifactWriteError, OSError) as exc:
        raise SummaryGenerationError(f"Failed to write run summary: {run.run_id}") from exc
    return summary_path


def render_run_summary(
    *,
    run: RunArtifacts,
    issues: list[SummaryIssue],
    errors: list[str],
) -> str:
    status_counts = Counter(issue.readiness_status for issue in issues)
    risk_counts = Counter(issue.risk_level for issue in issues)
    issue_errors = [issue for issue in issues if issue.error]

    lines = [
        "# Ticket Readiness Run Summary",
        "",
        f"Run ID: `{run.run_id}`",
        f"Total Issues: {len(issues)}",
        "",
        "## Readiness Counts",
        "",
        _counter_lines(status_counts),
        "",
        "## Risk Counts",
        "",
        _counter_lines(risk_counts),
        "",
        "## Issue Results",
        "",
        _issue_table(issues),
        "",
        "## Errors",
        "",
        _error_lines(errors, issue_errors),
        "",
        "## Skipped Or Pending Write-Back",
        "",
        _skipped_lines(issues),
        "",
    ]
    return "\n".join(lines)


def _counter_lines(counter: Counter[str]) -> str:
    if not counter:
        return "- None."
    return "\n".join(f"- {key}: {counter[key]}" for key in sorted(counter))


def _issue_table(issues: list[SummaryIssue]) -> str:
    if not issues:
        return "No issues were processed."

    lines = [
        "| Issue | Readiness | Risk | Report | Draft | Write-Back |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for issue in issues:
        report_path = issue.report.markdown_path if issue.report else ""
        draft_path = issue.draft_path or ""
        lines.append(
            f"| {issue.issue_id} {issue.title} | {issue.readiness_status} | "
            f"{issue.risk_level} | {report_path} | {draft_path} | {issue.writeback_status} |"
        )
    return "\n".join(lines)


def _error_lines(errors: list[str], issue_errors: list[SummaryIssue]) -> str:
    lines = [f"- {error}" for error in errors]
    lines.extend(f"- {issue.issue_id}: {issue.error}" for issue in issue_errors if issue.error)
    if not lines:
        return "- None."
    return "\n".join(lines)


def _skipped_lines(issues: list[SummaryIssue]) -> str:
    skipped = [
        issue
        for issue in issues
        if issue.writeback_status in {"skipped", "not_attempted", "blocked", "failed"}
    ]
    if not skipped:
        return "- None."
    return "\n".join(f"- {issue.issue_id}: {issue.writeback_status}" for issue in skipped)
