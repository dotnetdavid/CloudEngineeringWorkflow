from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from ticket_readiness.artifacts import ArtifactWriteError, RunArtifacts
from ticket_readiness.errors import TicketReadinessError
from ticket_readiness.linear import LinearIssue
from ticket_readiness.llm_analysis import LLMAnalysis


class DraftGenerationError(TicketReadinessError):
    """Raised when a draft comment cannot be generated safely."""


@dataclass(frozen=True)
class DraftComment:
    issue_id: str
    path: str
    sha256: str


def generate_draft_comment(
    *,
    run: RunArtifacts,
    issue: LinearIssue,
    llm_analysis: LLMAnalysis | None,
) -> DraftComment:
    if llm_analysis is None:
        raise DraftGenerationError(f"Cannot generate draft without valid analysis: {issue.identifier}")

    relative_path = f"drafts/{issue.identifier.replace('/', '-')}-linear-comment.md"
    content = render_draft_comment(issue=issue, llm_analysis=llm_analysis)

    try:
        draft_path = run.path(relative_path)
        draft_path.write_text(content, encoding="utf-8")
    except (ArtifactWriteError, OSError) as exc:
        raise DraftGenerationError(f"Failed to generate draft for {issue.identifier}") from exc

    return DraftComment(
        issue_id=issue.identifier,
        path=relative_path,
        sha256=compute_draft_hash(draft_path),
    )


def render_draft_comment(*, issue: LinearIssue, llm_analysis: LLMAnalysis) -> str:
    return "\n".join(
        [
            "<!-- generated-by: ticket-readiness-workflow -->",
            f"Target Issue: `{issue.identifier}`",
            f"Readiness: `{llm_analysis.readiness_status}`",
            f"Risk: `{llm_analysis.risk_level}`",
            "",
            "## Summary",
            "",
            llm_analysis.summary,
            "",
            "## Missing Information",
            "",
            _bullet_list(llm_analysis.missing_information),
            "",
            "## Grooming Questions",
            "",
            _bullet_list(llm_analysis.grooming_questions),
            "",
            "## Risk Notes",
            "",
            _bullet_list(llm_analysis.operational_risk),
            "",
            "## Security Notes",
            "",
            _bullet_list(llm_analysis.security_notes),
            "",
            "## Recommendation",
            "",
            llm_analysis.recommended_next_action,
            "",
            "## Draft Comment",
            "",
            llm_analysis.draft_comment,
            "",
        ]
    )


def compute_draft_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as draft_file:
        for chunk in iter(lambda: draft_file.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bullet_list(items: tuple[str, ...]) -> str:
    if not items:
        return "- None noted."
    return "\n".join(f"- {item}" for item in items)
