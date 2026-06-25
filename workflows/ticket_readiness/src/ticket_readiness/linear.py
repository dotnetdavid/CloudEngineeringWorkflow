from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from ticket_readiness.errors import TicketReadinessError
from ticket_readiness.http_config import safe_http_error_detail, validate_timeout_seconds
from ticket_readiness.rate_limit import RateLimitError

LINEAR_GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"

PROJECT_ISSUES_QUERY = """
query TicketReadinessProjectIssues($projectId: String!, $cursor: String) {
  project(id: $projectId) {
    issues(first: 100, after: $cursor, orderBy: updatedAt) {
      nodes {
        id
        identifier
        title
        description
        url
        priority
        estimate
        state {
          name
          type
        }
        labels {
          nodes {
            name
          }
        }
        project {
          id
          name
        }
        team {
          id
          name
          key
        }
        createdAt
        updatedAt
        creator {
          id
          name
          email
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_LINEAR_IDENTIFIER_PATTERN = re.compile(r"^[A-Z0-9]+-[0-9]+$")


class LinearReadError(TicketReadinessError):
    """Raised when Linear data cannot be read safely."""


class LinearGraphQLTransport(Protocol):
    def execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Execute a read-only GraphQL request."""


class RateLimiter(Protocol):
    def wait(self) -> None:
        """Throttle before an external API call."""


@dataclass(frozen=True)
class LinearPriority:
    value: int | float | None = None
    name: str | None = None


@dataclass(frozen=True)
class LinearIssue:
    identifier: str
    title: str
    description: str = ""
    internal_id: str | None = None
    url: str | None = None
    priority: LinearPriority = LinearPriority()
    estimate: int | float | None = None
    status: str | None = None
    status_type: str | None = None
    labels: tuple[str, ...] = ()
    project_id: str | None = None
    project_name: str | None = None
    team_id: str | None = None
    team_name: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    creator: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["labels"] = list(self.labels)
        return payload


class LinearGraphQLClient:
    """Execute authenticated read-only GraphQL requests against Linear."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str = LINEAR_GRAPHQL_ENDPOINT,
        timeout_seconds: int = 30,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("LINEAR_API_KEY")
        self._endpoint = endpoint
        self._timeout_seconds = validate_timeout_seconds(timeout_seconds)
        self._rate_limiter = rate_limiter

    def execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        if not self._api_key:
            raise LinearReadError("LINEAR_API_KEY is required for live Linear reads.")

        request = urllib.request.Request(
            self._endpoint,
            data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": self._api_key,
            },
            method="POST",
        )

        try:
            if self._rate_limiter is not None:
                self._rate_limiter.wait()
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise LinearReadError("Linear GraphQL request was rate limited.") from RateLimitError(
                    "Linear GraphQL request was rate limited."
                )
            detail = safe_http_error_detail(exc.read())
            raise LinearReadError(
                f"Linear GraphQL request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise LinearReadError(f"Linear GraphQL request failed: {exc.reason}") from exc

        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise LinearReadError("Linear GraphQL response was not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise LinearReadError("Linear GraphQL response must be a JSON object.")

        errors = payload.get("errors")
        if errors:
            raise LinearReadError(f"Linear GraphQL returned errors: {_error_summary(errors)}")

        return dict(payload)


class LinearIssueReader:
    """Read and normalize issues from a single Linear project."""

    def __init__(self, client: LinearGraphQLTransport) -> None:
        self._client = client

    def read_project_issues(self, project_id: str, *, max_issues: int | None = None) -> list[LinearIssue]:
        issues: list[LinearIssue] = []
        cursor: str | None = None

        try:
            while True:
                response = self._client.execute(
                    PROJECT_ISSUES_QUERY,
                    {"projectId": project_id, "cursor": cursor},
                )
                connection = _issues_connection(response, project_id)
                for issue in connection.get("nodes", []):
                    if max_issues is not None and len(issues) >= max_issues:
                        raise LinearReadError(
                            f"Linear project issue count exceeds configured max_issues: {max_issues}"
                        )
                    issues.append(normalize_issue(issue))

                page_info = connection.get("pageInfo") or {}
                if not page_info.get("hasNextPage"):
                    return issues
                cursor = page_info.get("endCursor")
                if not cursor:
                    raise LinearReadError("Linear pagination reported another page without a cursor.")
        except LinearReadError:
            raise
        except Exception as exc:
            raise LinearReadError(f"Failed to read Linear issues for project {project_id}.") from exc


def normalize_issue(raw_issue: dict[str, Any]) -> LinearIssue:
    """Convert a Linear API or fixture payload into the internal issue model."""
    identifier = str(raw_issue.get("identifier") or raw_issue.get("id") or "").strip()
    if not identifier:
        raise LinearReadError("Linear issue payload is missing both identifier and id.")
    if not _LINEAR_IDENTIFIER_PATTERN.match(identifier):
        raise LinearReadError(
            f"Invalid Linear issue identifier: {identifier}. Expected format like ASG-40."
        )

    return LinearIssue(
        identifier=identifier,
        internal_id=_internal_id(raw_issue, identifier),
        title=str(raw_issue.get("title") or ""),
        description=str(raw_issue.get("description") or ""),
        url=_optional_str(raw_issue.get("url")),
        priority=_priority(raw_issue.get("priority")),
        estimate=raw_issue.get("estimate"),
        status=_status(raw_issue),
        status_type=_status_type(raw_issue),
        labels=_labels(raw_issue.get("labels")),
        project_id=_related_id(raw_issue, "project", "projectId"),
        project_name=_related_name(raw_issue, "project"),
        team_id=_related_id(raw_issue, "team", "teamId"),
        team_name=_related_name(raw_issue, "team"),
        created_at=_optional_str(raw_issue.get("createdAt")),
        updated_at=_optional_str(raw_issue.get("updatedAt")),
        creator=_creator(raw_issue),
    )


def _issues_connection(response: dict[str, Any], project_id: str) -> dict[str, Any]:
    project = (response.get("data") or {}).get("project")
    if project is None:
        raise LinearReadError(f"Linear project was not found or not readable: {project_id}")

    connection = project.get("issues")
    if not isinstance(connection, dict):
        raise LinearReadError(f"Linear project response did not include issues: {project_id}")

    return connection


def _internal_id(raw_issue: dict[str, Any], identifier: str) -> str | None:
    explicit = raw_issue.get("internal_id") or raw_issue.get("internalId")
    if explicit:
        return str(explicit)

    raw_id = raw_issue.get("id")
    if isinstance(raw_id, str) and raw_id != identifier and _UUID_PATTERN.match(raw_id):
        return raw_id

    return None


def _priority(raw_priority: Any) -> LinearPriority:
    if isinstance(raw_priority, dict):
        return LinearPriority(value=raw_priority.get("value"), name=_optional_str(raw_priority.get("name")))

    if isinstance(raw_priority, (int, float)):
        return LinearPriority(value=raw_priority)

    return LinearPriority()


def _labels(raw_labels: Any) -> tuple[str, ...]:
    if raw_labels is None:
        return ()

    labels = raw_labels.get("nodes", []) if isinstance(raw_labels, dict) else raw_labels
    normalized: list[str] = []

    for label in labels:
        if isinstance(label, dict):
            name = label.get("name")
        else:
            name = label
        if name:
            normalized.append(str(name))

    return tuple(normalized)


def _status(raw_issue: dict[str, Any]) -> str | None:
    state = raw_issue.get("state")
    if isinstance(state, dict):
        return _optional_str(state.get("name"))
    return _optional_str(raw_issue.get("status"))


def _status_type(raw_issue: dict[str, Any]) -> str | None:
    state = raw_issue.get("state")
    if isinstance(state, dict):
        return _optional_str(state.get("type"))
    return _optional_str(raw_issue.get("statusType"))


def _related_id(raw_issue: dict[str, Any], relation_field: str, flat_field: str) -> str | None:
    relation = raw_issue.get(relation_field)
    if isinstance(relation, dict):
        return _optional_str(relation.get("id"))
    return _optional_str(raw_issue.get(flat_field))


def _related_name(raw_issue: dict[str, Any], relation_field: str) -> str | None:
    relation = raw_issue.get(relation_field)
    if isinstance(relation, dict):
        return _optional_str(relation.get("name"))
    return _optional_str(relation)


def _creator(raw_issue: dict[str, Any]) -> str | None:
    creator = raw_issue.get("creator")
    if isinstance(creator, dict):
        return _optional_str(creator.get("name") or creator.get("email") or creator.get("id"))
    return _optional_str(raw_issue.get("createdBy"))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _error_summary(errors: Any) -> str:
    if not isinstance(errors, list):
        return str(errors)

    messages = []
    for error in errors[:3]:
        if isinstance(error, dict) and error.get("message"):
            messages.append(str(error["message"]))
        else:
            messages.append(str(error))
    return "; ".join(messages)
