from __future__ import annotations

from pathlib import Path

import pytest

from ticket_readiness.artifacts import ArtifactStore
from ticket_readiness.drafts import DraftGenerationError, compute_draft_hash, generate_draft_comment
from ticket_readiness.linear import LinearIssue, LinearPriority
from ticket_readiness.llm_analysis import validate_model_output


def test_generate_draft_comment_writes_reviewable_markdown(tmp_path):
    run = _run(tmp_path)
    issue = _issue()
    analysis = validate_model_output(_llm_output())

    draft = generate_draft_comment(run=run, issue=issue, llm_analysis=analysis)

    assert draft.issue_id == "ASG-40"
    assert draft.path == "drafts/ASG-40-linear-comment.md"
    assert len(draft.sha256) == 64

    content = run.path(draft.path).read_text(encoding="utf-8")
    assert "<!-- generated-by: ticket-readiness-workflow -->" in content
    assert "Target Issue: `ASG-40`" in content
    assert "Readiness: `needs_grooming`" in content
    assert "Who owns the route table update?" in content
    assert "Clarify owner and route table scope before sprint commitment." in content


def test_compute_draft_hash_is_stable_and_content_sensitive(tmp_path):
    path = tmp_path / "draft.md"
    path.write_text("same content\n", encoding="utf-8")

    first = compute_draft_hash(path)
    second = compute_draft_hash(path)

    path.write_text("different content\n", encoding="utf-8")
    changed = compute_draft_hash(path)

    assert first == second
    assert first != changed


def test_draft_target_issue_id_comes_from_workflow_issue_not_model_output(tmp_path):
    run = _run(tmp_path)
    issue = _issue()
    analysis = validate_model_output(_llm_output(draft_comment="Please update ASG-999 instead."))

    draft = generate_draft_comment(run=run, issue=issue, llm_analysis=analysis)

    content = run.path(draft.path).read_text(encoding="utf-8")
    assert "Target Issue: `ASG-40`" in content
    assert "Target Issue: `ASG-999`" not in content


def test_invalid_analysis_produces_no_draft(tmp_path):
    run = _run(tmp_path)

    with pytest.raises(DraftGenerationError):
        generate_draft_comment(run=run, issue=_issue(), llm_analysis=None)

    assert not list(run.path("drafts").glob("*.md"))


def _run(tmp_path: Path):
    return ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )


def _issue() -> LinearIssue:
    return LinearIssue(
        identifier="ASG-40",
        title="Add S3 VPC endpoint for private artifact bucket access",
        description="Acceptance Criteria: endpoint exists. Validation: verify S3 access.",
        priority=LinearPriority(value=2, name="High"),
        estimate=3,
    )


def _llm_output(**overrides):
    output = {
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
    output.update(overrides)
    return output
