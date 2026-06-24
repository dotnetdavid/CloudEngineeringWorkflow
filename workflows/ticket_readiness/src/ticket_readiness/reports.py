from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ticket_readiness.artifacts import ArtifactWriteError, RunArtifacts
from ticket_readiness.errors import TicketReadinessError
from ticket_readiness.linear import LinearIssue
from ticket_readiness.llm_analysis import LLMAnalysis
from ticket_readiness.readiness import DeterministicReadinessResult


class ReportGenerationError(TicketReadinessError):
    """Raised when readiness reports cannot be written safely."""


@dataclass(frozen=True)
class IssueReport:
    issue_id: str
    markdown_path: str
    json_path: str
    readiness_status: str
    readiness_score: int
    risk_level: str


def generate_issue_report(
    *,
    run: RunArtifacts,
    issue: LinearIssue,
    deterministic_result: DeterministicReadinessResult,
    llm_analysis: LLMAnalysis,
    draft_comment_path: str,
) -> IssueReport:
    issue_slug = issue.identifier.replace("/", "-")
    markdown_path = f"reports/{issue_slug}-readiness.md"
    json_path = f"reports/{issue_slug}-readiness.json"

    payload = build_report_payload(
        issue=issue,
        deterministic_result=deterministic_result,
        llm_analysis=llm_analysis,
        draft_comment_path=draft_comment_path,
    )

    try:
        run.write_json(json_path, payload)
        run.path(markdown_path).write_text(
            render_markdown_report(payload),
            encoding="utf-8",
        )
    except (ArtifactWriteError, OSError) as exc:
        raise ReportGenerationError(f"Failed to generate report for {issue.identifier}") from exc

    return IssueReport(
        issue_id=issue.identifier,
        markdown_path=markdown_path,
        json_path=json_path,
        readiness_status=llm_analysis.readiness_status,
        readiness_score=payload["readiness_score"],
        risk_level=llm_analysis.risk_level,
    )


def build_report_payload(
    *,
    issue: LinearIssue,
    deterministic_result: DeterministicReadinessResult,
    llm_analysis: LLMAnalysis,
    draft_comment_path: str,
) -> dict[str, Any]:
    dimension_scores = _dimension_scores(deterministic_result)
    return {
        "issue_id": issue.identifier,
        "issue_title": issue.title,
        "issue_url": issue.url,
        "readiness_status": llm_analysis.readiness_status,
        "readiness_score": _readiness_score(dimension_scores),
        "work_type": llm_analysis.work_type,
        "risk_level": llm_analysis.risk_level,
        "dimension_scores": dimension_scores,
        "missing_information": list(llm_analysis.missing_information),
        "grooming_questions": list(llm_analysis.grooming_questions),
        "operational_risk": list(llm_analysis.operational_risk),
        "security_notes": list(llm_analysis.security_notes),
        "acceptance_criteria_improvements": list(llm_analysis.acceptance_criteria_improvements),
        "recommended_next_action": llm_analysis.recommended_next_action,
        "evidence": _evidence(deterministic_result),
        "deterministic_findings": [
            finding.to_dict() for finding in deterministic_result.findings
        ],
        "risk_flags": [flag.to_dict() for flag in deterministic_result.risk_flags],
        "model_metadata": llm_analysis.model_metadata,
        "draft_comment_path": draft_comment_path,
    }


def render_markdown_report(payload: dict[str, Any]) -> str:
    source_url = payload.get("issue_url") or "not provided"
    return "\n".join(
        [
            f"# {payload['issue_id']}: {payload['issue_title']}",
            "",
            f"Source: {source_url}",
            f"Readiness: `{payload['readiness_status']}`",
            f"Score: `{payload['readiness_score']}`",
            f"Work Type: `{payload['work_type']}`",
            f"Risk Level: `{payload['risk_level']}`",
            f"Draft Comment: `{payload['draft_comment_path']}`",
            "",
            "## Summary",
            "",
            payload.get("summary") or _summary_from_payload(payload),
            "",
            "## Evidence From Ticket",
            "",
            _bullet_list(payload["evidence"]),
            "",
            "## Missing Information",
            "",
            _bullet_list(payload["missing_information"]),
            "",
            "## Grooming Questions",
            "",
            _bullet_list(payload["grooming_questions"]),
            "",
            "## Operational Risk",
            "",
            _bullet_list(payload["operational_risk"]),
            "",
            "## Security Notes",
            "",
            _bullet_list(payload["security_notes"]),
            "",
            "## Acceptance Criteria Improvements",
            "",
            _bullet_list(payload["acceptance_criteria_improvements"]),
            "",
            "## Recommended Next Action",
            "",
            payload["recommended_next_action"],
            "",
            "## Deterministic Findings",
            "",
            _finding_table(payload["deterministic_findings"]),
            "",
        ]
    )


def _dimension_scores(result: DeterministicReadinessResult) -> dict[str, int]:
    scores: dict[str, int] = {}
    for finding in result.findings:
        if finding.status == "present":
            scores[finding.dimension] = 1
        elif finding.status == "not_applicable":
            scores[finding.dimension] = 1
        else:
            scores[finding.dimension] = 0
    return scores


def _readiness_score(dimension_scores: dict[str, int]) -> int:
    if not dimension_scores:
        return 0
    return round((sum(dimension_scores.values()) / len(dimension_scores)) * 100)


def _evidence(result: DeterministicReadinessResult) -> list[str]:
    evidence: list[str] = []
    for finding in result.findings:
        evidence.extend(finding.evidence)
    for flag in result.risk_flags:
        evidence.extend(flag.evidence)
    return sorted(set(evidence))


def _summary_from_payload(payload: dict[str, Any]) -> str:
    return (
        f"{payload['issue_id']} is classified as {payload['readiness_status']} "
        f"with {payload['risk_level']} risk."
    )


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "- None noted."
    return "\n".join(f"- {item}" for item in items)


def _finding_table(findings: list[dict[str, Any]]) -> str:
    lines = ["| Dimension | Status | Required | Message |", "| --- | --- | --- | --- |"]
    for finding in findings:
        lines.append(
            "| {dimension} | {status} | {required} | {message} |".format(
                dimension=finding["dimension"],
                status=finding["status"],
                required=str(finding["required"]).lower(),
                message=str(finding["message"]).replace("|", "\\|"),
            )
        )
    return "\n".join(lines)
