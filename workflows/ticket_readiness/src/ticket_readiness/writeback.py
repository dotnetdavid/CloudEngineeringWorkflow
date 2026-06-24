from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from ticket_readiness.approvals import ApprovalError, validate_approval_record
from ticket_readiness.artifacts import ArtifactWriteError, RunArtifacts
from ticket_readiness.http_config import validate_timeout_seconds
from ticket_readiness.linear import LINEAR_GRAPHQL_ENDPOINT

CREATE_COMMENT_MUTATION = """
mutation TicketReadinessCreateComment($issueId: String!, $body: String!) {
  commentCreate(input: {issueId: $issueId, body: $body}) {
    success
    comment {
      id
      url
    }
  }
}
"""


class WriteBackError(RuntimeError):
    """Raised when approved Linear write-back cannot be completed."""


class LinearCommentClient(Protocol):
    def create_comment(self, *, issue_id: str, body: str) -> dict[str, Any]:
        """Create a Linear comment for an issue."""


@dataclass(frozen=True)
class WriteBackResult:
    issue_id: str
    comment_id: str
    draft_path: str


class HTTPLinearCommentClient:
    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str = LINEAR_GRAPHQL_ENDPOINT,
        timeout_seconds: int = 30,
    ) -> None:
        self._api_key = api_key or os.environ.get("LINEAR_API_KEY")
        self._endpoint = endpoint
        self._timeout_seconds = validate_timeout_seconds(timeout_seconds)

    def create_comment(self, *, issue_id: str, body: str) -> dict[str, Any]:
        if not self._api_key:
            raise WriteBackError("LINEAR_API_KEY is required for live Linear comment write-back.")

        request = urllib.request.Request(
            self._endpoint,
            data=json.dumps(
                {
                    "query": CREATE_COMMENT_MUTATION,
                    "variables": {"issueId": issue_id, "body": body},
                }
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": self._api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise WriteBackError(
                f"Linear comment request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise WriteBackError(f"Linear comment request failed: {exc}") from exc

        if payload.get("errors"):
            raise WriteBackError(f"Linear comment request returned errors: {payload['errors']}")

        result = ((payload.get("data") or {}).get("commentCreate") or {})
        if not result.get("success"):
            raise WriteBackError("Linear comment request did not report success.")

        return result.get("comment") or {}


class LinearCommentWriteBack:
    def __init__(self, client: LinearCommentClient) -> None:
        self._client = client

    def post_approved(
        self,
        *,
        run: RunArtifacts,
        issue_id: str,
        draft_relative_path: str,
    ) -> WriteBackResult:
        try:
            approval = validate_approval_record(
                run=run,
                issue_id=issue_id,
                draft_relative_path=draft_relative_path,
            )
            body = run.path(draft_relative_path).read_text(encoding="utf-8")
            response = self._client.create_comment(issue_id=issue_id, body=body)
            comment_id = str(response.get("id") or "")
            if not comment_id:
                raise WriteBackError("Linear comment response did not include a comment id.")
            _record_posted_comment_id(run, approval.path, comment_id)
            run.append_event(
                event_type="linear_comment_written",
                state="succeeded",
                issue_id=issue_id,
                message=f"Posted approved draft comment {comment_id}.",
            )
            return WriteBackResult(
                issue_id=issue_id,
                comment_id=comment_id,
                draft_path=draft_relative_path,
            )
        except (ApprovalError, OSError, ArtifactWriteError, WriteBackError) as exc:
            _log_failure(run, issue_id, str(exc))
            raise WriteBackError(str(exc)) from exc
        except Exception as exc:
            _log_failure(run, issue_id, str(exc))
            raise WriteBackError(f"Failed to post approved Linear comment for {issue_id}") from exc


def _record_posted_comment_id(run: RunArtifacts, approval_path: str | None, comment_id: str) -> None:
    if not approval_path:
        raise WriteBackError("Approval record path is missing.")
    path = run.path(approval_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["posted_comment_id"] = comment_id
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _log_failure(run: RunArtifacts, issue_id: str, message: str) -> None:
    try:
        run.append_event(
            event_type="linear_comment_write_failed",
            state="failed",
            issue_id=issue_id,
            message=message,
        )
    except Exception:
        pass
