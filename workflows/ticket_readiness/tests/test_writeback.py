from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
import urllib.error

import pytest

from ticket_readiness.approvals import write_approval_template
from ticket_readiness.artifacts import ArtifactStore
from ticket_readiness.writeback import HTTPLinearCommentClient, LinearCommentWriteBack, WriteBackError


def test_writeback_posts_only_after_valid_approval_and_records_comment_id(tmp_path):
    run = _approved_run(tmp_path)
    client = FakeCommentClient({"id": "comment-123"})
    writer = LinearCommentWriteBack(client=client)

    result = writer.post_approved(
        run=run,
        issue_id="ASG-40",
        draft_relative_path="drafts/ASG-40-linear-comment.md",
    )

    assert result.issue_id == "ASG-40"
    assert result.comment_id == "comment-123"
    assert client.calls == [{"issue_id": "ASG-40", "body": "draft comment\n"}]

    approval = json.loads(run.path("approvals", "ASG-40-approval.json").read_text(encoding="utf-8"))
    assert approval["posted_comment_id"] == "comment-123"


def test_writeback_blocks_missing_or_unapproved_approval(tmp_path):
    run = _run(tmp_path)
    run.path("drafts", "ASG-40-linear-comment.md").write_text("draft comment\n", encoding="utf-8")
    client = FakeCommentClient({"id": "comment-123"})

    with pytest.raises(WriteBackError):
        LinearCommentWriteBack(client=client).post_approved(
            run=run,
            issue_id="ASG-40",
            draft_relative_path="drafts/ASG-40-linear-comment.md",
        )

    assert client.calls == []


def test_writeback_does_not_retry_indefinitely_and_logs_failure(tmp_path):
    run = _approved_run(tmp_path)
    client = FailingCommentClient()

    with pytest.raises(WriteBackError):
        LinearCommentWriteBack(client=client).post_approved(
            run=run,
            issue_id="ASG-40",
            draft_relative_path="drafts/ASG-40-linear-comment.md",
        )

    assert client.calls == 1
    events = run.path("events.jsonl").read_text(encoding="utf-8").splitlines()
    assert any("linear_comment_write_failed" in event for event in events)


def test_writeback_client_only_exposes_comment_creation():
    assert hasattr(LinearCommentWriteBack, "post_approved")
    assert not hasattr(LinearCommentWriteBack, "update_status")
    assert not hasattr(LinearCommentWriteBack, "update_priority")
    assert not hasattr(LinearCommentWriteBack, "update_description")


@pytest.mark.parametrize("timeout_seconds", [0, -1, 301])
def test_http_comment_client_rejects_invalid_timeout(timeout_seconds):
    with pytest.raises(ValueError, match="timeout_seconds"):
        HTTPLinearCommentClient(api_key="linear-key", timeout_seconds=timeout_seconds)


@pytest.mark.parametrize("timeout_seconds", [1, 300])
def test_http_comment_client_accepts_valid_timeout(timeout_seconds):
    HTTPLinearCommentClient(api_key="linear-key", timeout_seconds=timeout_seconds)


def test_http_comment_client_redacts_secret_like_error_details(monkeypatch):
    secret = "sk" + "-proj-" + "c" * 40

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            500,
            "Internal Server Error",
            hdrs={},
            fp=BytesIO(f'{{"error":"failed with {secret}"}}'.encode("utf-8")),
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(WriteBackError) as exc_info:
        HTTPLinearCommentClient(api_key="linear-key").create_comment(issue_id="ASG-40", body="draft")

    message = str(exc_info.value)
    assert "HTTP 500" in message
    assert secret not in message
    assert "[REDACTED_SECRET]" in message


def _approved_run(tmp_path: Path):
    run = _run(tmp_path)
    run.path("drafts", "ASG-40-linear-comment.md").write_text("draft comment\n", encoding="utf-8")
    template = write_approval_template(
        run=run,
        issue_id="ASG-40",
        draft_relative_path="drafts/ASG-40-linear-comment.md",
    )
    approval_path = run.path(template.path)
    payload = json.loads(approval_path.read_text(encoding="utf-8"))
    payload["decision"] = "approved"
    approval_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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


class FakeCommentClient:
    def __init__(self, response: dict):
        self._response = response
        self.calls: list[dict] = []

    def create_comment(self, *, issue_id: str, body: str) -> dict:
        self.calls.append({"issue_id": issue_id, "body": body})
        return self._response


class FailingCommentClient:
    def __init__(self):
        self.calls = 0

    def create_comment(self, *, issue_id: str, body: str) -> dict:
        self.calls += 1
        raise RuntimeError("Linear unavailable")
