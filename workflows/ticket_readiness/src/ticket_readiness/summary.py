from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any

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
    run_errors = errors or []
    metrics = collect_run_metrics(run=run, issues=issues, errors=run_errors)
    content = render_run_summary(run=run, issues=issues, errors=run_errors, metrics=metrics)
    try:
        _update_manifest_metrics(run=run, issues=issues, metrics=metrics)
        run.path(summary_path).write_text(content, encoding="utf-8")
    except (ArtifactWriteError, OSError) as exc:
        raise SummaryGenerationError(f"Failed to write run summary: {run.run_id}") from exc
    return summary_path


def render_run_summary(
    *,
    run: RunArtifacts,
    issues: list[SummaryIssue],
    errors: list[str],
    metrics: dict[str, Any] | None = None,
) -> str:
    run_metrics = metrics or collect_run_metrics(run=run, issues=issues, errors=errors)
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
        "## Workflow Metrics",
        "",
        _metrics_lines(run_metrics),
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


def collect_run_metrics(
    *,
    run: RunArtifacts,
    issues: list[SummaryIssue],
    errors: list[str],
) -> dict[str, Any]:
    issue_errors = [issue for issue in issues if issue.error]
    report_metadata = _report_model_metadata(run, issues)
    usage = _model_usage(report_metadata)
    latency = _model_latency(report_metadata)

    return {
        "issues_processed": len(issues),
        "issue_analysis": {
            "succeeded": sum(1 for issue in issues if not issue.error),
            "failed": len(issue_errors),
        },
        "run_errors": len(errors),
        "issue_errors": len(issue_errors),
        "phase_events": _phase_event_counts(run),
        "api_calls": {
            "openai_responses": {
                "known": sum(1 for metadata in report_metadata if metadata),
            }
        },
        "model_usage": usage,
        "model_latency": latency,
        "errors": _manifest_errors(errors, issue_errors),
    }


def _counter_lines(counter: Counter[str]) -> str:
    if not counter:
        return "- None."
    return "\n".join(f"- {key}: {counter[key]}" for key in sorted(counter))


def _metrics_lines(metrics: dict[str, Any]) -> str:
    issue_analysis = metrics["issue_analysis"]
    api_calls = metrics["api_calls"]["openai_responses"]
    model_usage = metrics["model_usage"]
    model_latency = metrics["model_latency"]
    return "\n".join(
        [
            f"- Issues processed: {metrics['issues_processed']}",
            f"- Issue analysis succeeded: {issue_analysis['succeeded']}",
            f"- Issue analysis failed: {issue_analysis['failed']}",
            f"- Run-level errors: {metrics['run_errors']}",
            f"- Known OpenAI response calls: {api_calls['known']}",
            f"- Model usage total tokens: {model_usage.get('total_tokens', 0)}",
            f"- Model latency samples: {model_latency.get('samples', 0)}",
        ]
    )


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


def _update_manifest_metrics(
    *,
    run: RunArtifacts,
    issues: list[SummaryIssue],
    metrics: dict[str, Any],
) -> None:
    manifest_path = run.path("manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SummaryGenerationError(f"Failed to update manifest metrics: {run.run_id}") from exc
    if not isinstance(manifest, dict):
        raise SummaryGenerationError(f"Manifest must contain an object: {run.run_id}")

    manifest["issue_ids"] = [issue.issue_id for issue in issues]
    manifest["counts"] = {
        key: value
        for key, value in metrics.items()
        if key != "errors"
    }
    manifest["errors"] = metrics["errors"]
    run.write_json("manifest.json", manifest)


def _phase_event_counts(run: RunArtifacts) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = {}
    events_path = run.path("events.jsonl")
    if not events_path.exists():
        return {}

    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            counts.setdefault("event_log", Counter())["failed"] += 1
            continue
        event_type = str(event.get("event_type") or "unknown")
        state = str(event.get("state") or "unknown")
        phase = _metric_phase(event_type)
        counts.setdefault(phase, Counter())[state] += 1

    return {
        phase: dict(sorted(state_counts.items()))
        for phase, state_counts in sorted(counts.items())
    }


def _metric_phase(event_type: str) -> str:
    if event_type in {"issue_analyzed", "issue_analysis_failed"}:
        return "issue_analysis"
    return event_type


def _report_model_metadata(run: RunArtifacts, issues: list[SummaryIssue]) -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []
    for issue in issues:
        if issue.report is None:
            continue
        report_path = run.path(issue.report.json_path)
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        model_metadata = payload.get("model_metadata")
        if isinstance(model_metadata, dict):
            metadata.append(model_metadata)
    return metadata


def _model_usage(metadata_items: list[dict[str, Any]]) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for metadata in metadata_items:
        usage = metadata.get("usage")
        if not isinstance(usage, dict):
            continue
        for key, value in usage.items():
            if isinstance(value, int):
                totals[key] += value
    return dict(sorted(totals.items()))


def _model_latency(metadata_items: list[dict[str, Any]]) -> dict[str, int]:
    values: list[int] = []
    for metadata in metadata_items:
        latency_ms = _latency_milliseconds(metadata)
        if latency_ms is not None:
            values.append(latency_ms)
    if not values:
        return {"samples": 0}
    return {
        "samples": len(values),
        "min_ms": min(values),
        "max_ms": max(values),
        "total_ms": sum(values),
        "average_ms": round(sum(values) / len(values)),
    }


def _latency_milliseconds(metadata: dict[str, Any]) -> int | None:
    latency_ms = metadata.get("latency_ms")
    if isinstance(latency_ms, int):
        return latency_ms
    latency_seconds = metadata.get("latency_seconds")
    if isinstance(latency_seconds, (int, float)):
        return round(latency_seconds * 1000)
    return None


def _manifest_errors(errors: list[str], issue_errors: list[SummaryIssue]) -> list[str]:
    manifest_errors = list(errors)
    manifest_errors.extend(
        f"{issue.issue_id}: {issue.error}" for issue in issue_errors if issue.error
    )
    return manifest_errors
