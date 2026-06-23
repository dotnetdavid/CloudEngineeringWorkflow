from __future__ import annotations

import json
from pathlib import Path

import pytest

from ticket_readiness.approvals import (
    ApprovalError,
    ApprovalRecord,
    validate_approval_record,
    write_approval_template,
)
from ticket_readiness.artifacts import ArtifactStore


def test_write_approval_template_requires_manual_decision(tmp_path):
    run = _run(tmp_path)
    draft_path = run.path("drafts", "ASG-40-linear-comment.md")
    draft_path.write_text("draft comment\n", encoding="utf-8")

    template = write_approval_template(
        run=run,
        issue_id="ASG-40",
        draft_relative_path="drafts/ASG-40-linear-comment.md",
        approved_by="Dave",
    )

    payload = json.loads(run.path(template.path).read_text(encoding="utf-8"))
    assert payload["issue_id"] == "ASG-40"
    assert payload["decision"] == "skipped"
    assert payload["approved_by"] == "Dave"
    assert payload["draft_sha256"] == template.draft_sha256


def test_validate_approved_record_accepts_current_hash(tmp_path):
    run = _run(tmp_path)
    draft_path = run.path("drafts", "ASG-40-linear-comment.md")
    draft_path.write_text("draft comment\n", encoding="utf-8")
    template = write_approval_template(
        run=run,
        issue_id="ASG-40",
        draft_relative_path="drafts/ASG-40-linear-comment.md",
    )
    _update_approval(run.path(template.path), decision="approved")

    record = validate_approval_record(
        run=run,
        issue_id="ASG-40",
        draft_relative_path="drafts/ASG-40-linear-comment.md",
    )

    assert isinstance(record, ApprovalRecord)
    assert record.decision == "approved"


@pytest.mark.parametrize("decision", ["rejected", "skipped"])
def test_validate_blocks_non_approved_decisions(tmp_path, decision):
    run = _approved_run(tmp_path, decision=decision)

    with pytest.raises(ApprovalError, match="not approved"):
        validate_approval_record(
            run=run,
            issue_id="ASG-40",
            draft_relative_path="drafts/ASG-40-linear-comment.md",
        )


def test_missing_approval_blocks_write_back(tmp_path):
    run = _run(tmp_path)
    run.path("drafts", "ASG-40-linear-comment.md").write_text("draft\n", encoding="utf-8")

    with pytest.raises(ApprovalError, match="Approval record is missing"):
        validate_approval_record(
            run=run,
            issue_id="ASG-40",
            draft_relative_path="drafts/ASG-40-linear-comment.md",
        )


def test_changed_draft_requires_reapproval(tmp_path):
    run = _approved_run(tmp_path, decision="approved")
    run.path("drafts", "ASG-40-linear-comment.md").write_text("changed draft\n", encoding="utf-8")

    with pytest.raises(ApprovalError, match="stale"):
        validate_approval_record(
            run=run,
            issue_id="ASG-40",
            draft_relative_path="drafts/ASG-40-linear-comment.md",
        )


def test_issue_id_mismatch_blocks_write_back(tmp_path):
    run = _approved_run(tmp_path, decision="approved")
    _update_approval(run.path("approvals", "ASG-40-approval.json"), issue_id="ASG-999")

    with pytest.raises(ApprovalError, match="issue_id mismatch"):
        validate_approval_record(
            run=run,
            issue_id="ASG-40",
            draft_relative_path="drafts/ASG-40-linear-comment.md",
        )


def test_malformed_approval_blocks_write_back(tmp_path):
    run = _run(tmp_path)
    run.path("drafts", "ASG-40-linear-comment.md").write_text("draft\n", encoding="utf-8")
    run.path("approvals", "ASG-40-approval.json").write_text("{nope", encoding="utf-8")

    with pytest.raises(ApprovalError, match="malformed"):
        validate_approval_record(
            run=run,
            issue_id="ASG-40",
            draft_relative_path="drafts/ASG-40-linear-comment.md",
        )


def _approved_run(tmp_path: Path, *, decision: str):
    run = _run(tmp_path)
    run.path("drafts", "ASG-40-linear-comment.md").write_text("draft comment\n", encoding="utf-8")
    template = write_approval_template(
        run=run,
        issue_id="ASG-40",
        draft_relative_path="drafts/ASG-40-linear-comment.md",
    )
    _update_approval(run.path(template.path), decision=decision)
    return run


def _run(tmp_path: Path):
    return ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )


def _update_approval(path: Path, **updates):
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(updates)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
