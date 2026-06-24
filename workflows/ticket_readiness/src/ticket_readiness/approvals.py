from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ticket_readiness.artifacts import ArtifactWriteError, RunArtifacts
from ticket_readiness.drafts import compute_draft_hash
from ticket_readiness.errors import TicketReadinessError

APPROVAL_DECISIONS = {"approved", "rejected", "skipped"}


class ApprovalError(TicketReadinessError):
    """Raised when write-back approval is missing, stale, or invalid."""


@dataclass(frozen=True)
class ApprovalRecord:
    issue_id: str
    draft_path: str
    draft_sha256: str
    decision: str
    approved_by: str | None
    approved_at: str | None
    rationale: str | None = None
    posted_comment_id: str | None = None
    path: str | None = None
    decided_at: str | None = None


def write_approval_template(
    *,
    run: RunArtifacts,
    issue_id: str,
    draft_relative_path: str,
    approved_by: str | None = None,
    rationale: str | None = None,
) -> ApprovalRecord:
    draft_sha256 = compute_draft_hash(run.path(draft_relative_path))
    path = _approval_path(issue_id)
    record = ApprovalRecord(
        issue_id=issue_id,
        draft_path=draft_relative_path,
        draft_sha256=draft_sha256,
        decision="skipped",
        approved_by=approved_by,
        approved_at=None,
        rationale=rationale or "Manual review required. Change decision to approved, rejected, or skipped.",
        path=path,
    )
    try:
        run.write_json(path, _record_payload(record))
    except ArtifactWriteError as exc:
        raise ApprovalError(f"Failed to write approval template for {issue_id}") from exc
    return record


def validate_approval_record(
    *,
    run: RunArtifacts,
    issue_id: str,
    draft_relative_path: str,
) -> ApprovalRecord:
    approval_path = _approval_path(issue_id)
    full_path = run.path(approval_path)
    if not full_path.exists():
        raise ApprovalError(f"Approval record is missing: {approval_path}")

    try:
        payload = json.loads(full_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApprovalError(f"Approval record is malformed: {approval_path}") from exc

    record = _parse_record(payload, approval_path)

    if record.issue_id != issue_id:
        raise ApprovalError(f"Approval issue_id mismatch: expected {issue_id}, got {record.issue_id}")
    if record.draft_path != draft_relative_path:
        raise ApprovalError(
            f"Approval draft_path mismatch: expected {draft_relative_path}, got {record.draft_path}"
        )
    if record.decision != "approved":
        raise ApprovalError(f"Approval record is not approved: {record.decision}")

    current_hash = compute_draft_hash(run.path(draft_relative_path))
    if record.draft_sha256 != current_hash:
        raise ApprovalError("Approval record is stale: draft hash changed.")

    return record


def _parse_record(payload: dict[str, Any], approval_path: str) -> ApprovalRecord:
    try:
        issue_id = _required_string(payload, "issue_id")
        draft_path = _required_string(payload, "draft_path")
        draft_sha256 = _required_string(payload, "draft_sha256")
        decision = _required_string(payload, "decision")
        approved_by = _optional_string(payload.get("approved_by"))
        approved_at = _optional_string(payload.get("approved_at"))
        decided_at = _optional_string(payload.get("decided_at"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ApprovalError(f"Approval record is malformed: {approval_path}") from exc

    if decision not in APPROVAL_DECISIONS:
        raise ApprovalError(f"Approval record has unsupported decision: {decision}")
    if len(draft_sha256) != 64:
        raise ApprovalError(f"Approval record has malformed draft_sha256: {approval_path}")
    if decision == "approved":
        if not approved_by:
            raise ApprovalError("Approval record approved_by is required for approved decisions.")
        approved_at = _required_timestamp(payload, "approved_at")

    return ApprovalRecord(
        issue_id=issue_id,
        draft_path=draft_path,
        draft_sha256=draft_sha256,
        decision=decision,
        approved_by=approved_by,
        approved_at=approved_at,
        rationale=_optional_string(payload.get("rationale")),
        posted_comment_id=_optional_string(payload.get("posted_comment_id")),
        path=approval_path,
        decided_at=decided_at,
    )


def _record_payload(record: ApprovalRecord) -> dict[str, Any]:
    return {
        "issue_id": record.issue_id,
        "draft_path": record.draft_path,
        "draft_sha256": record.draft_sha256,
        "decision": record.decision,
        "approved_by": record.approved_by,
        "approved_at": record.approved_at,
        "rationale": record.rationale,
        "posted_comment_id": record.posted_comment_id,
    }


def _approval_path(issue_id: str) -> str:
    return f"approvals/{issue_id.replace('/', '-')}-approval.json"


def _required_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload[field_name]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field_name)
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def _required_timestamp(payload: dict[str, Any], field_name: str) -> str:
    try:
        value = _required_string(payload, field_name)
    except (KeyError, TypeError, ValueError) as exc:
        raise ApprovalError(f"Approval record {field_name} is required.") from exc
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalError(f"Approval record has malformed {field_name}.") from exc
    if parsed.tzinfo is None:
        raise ApprovalError(f"Approval record {field_name} must include a timezone.")
    return value
