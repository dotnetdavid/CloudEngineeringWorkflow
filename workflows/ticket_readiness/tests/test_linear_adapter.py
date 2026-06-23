from __future__ import annotations

import pytest

from ticket_readiness.linear import LinearIssueReader, LinearReadError, normalize_issue


def test_normalize_issue_from_linear_payload():
    raw_issue = {
        "id": "ASG-60",
        "title": "TR-012: Documentation And Demo",
        "description": "Document and demonstrate the workflow.",
        "priority": {"value": 3, "name": "Medium"},
        "url": "https://linear.app/asgard-ai-agency/issue/ASG-60/tr-012-documentation-and-demo",
        "createdAt": "2026-06-22T20:30:58.417Z",
        "updatedAt": "2026-06-22T20:35:24.907Z",
        "status": "Backlog",
        "statusType": "backlog",
        "labels": [{"name": "docs"}, "demo"],
        "project": "AI Workflow Sandbox - Ticket Readiness",
        "projectId": "8ff212c4-dfc7-4152-88e0-3dd65723a420",
        "team": "Asgard AI Agency",
        "teamId": "b578eff2-753f-4777-995a-d542d7c2b6f4",
        "createdBy": "dotnetdavid@gmail.com",
    }

    issue = normalize_issue(raw_issue)

    assert issue.identifier == "ASG-60"
    assert issue.internal_id is None
    assert issue.title == "TR-012: Documentation And Demo"
    assert issue.priority.value == 3
    assert issue.priority.name == "Medium"
    assert issue.status == "Backlog"
    assert issue.status_type == "backlog"
    assert issue.labels == ("docs", "demo")
    assert issue.project_id == "8ff212c4-dfc7-4152-88e0-3dd65723a420"
    assert issue.team_name == "Asgard AI Agency"
    assert issue.creator == "dotnetdavid@gmail.com"


def test_reader_reads_issues_by_project_id_with_pagination():
    client = FakeLinearClient(
        [
            {
                "data": {
                    "project": {
                        "issues": {
                            "nodes": [{"id": "ASG-49", "title": "TR-001: Project Scaffold"}],
                            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-2"},
                        }
                    }
                }
            },
            {
                "data": {
                    "project": {
                        "issues": {
                            "nodes": [{"id": "ASG-50", "title": "TR-002: Linear Read Adapter"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            },
        ]
    )
    reader = LinearIssueReader(client=client)

    issues = reader.read_project_issues("project-123")

    assert [issue.identifier for issue in issues] == ["ASG-49", "ASG-50"]
    assert client.calls[0]["variables"] == {"projectId": "project-123", "cursor": None}
    assert client.calls[1]["variables"] == {"projectId": "project-123", "cursor": "cursor-2"}
    assert all("mutation" not in call["query"].lower() for call in client.calls)


def test_reader_surfaces_read_failures_without_partial_results():
    reader = LinearIssueReader(client=FailingLinearClient())

    with pytest.raises(LinearReadError, match="Failed to read Linear issues"):
        reader.read_project_issues("project-123")


class FakeLinearClient:
    def __init__(self, responses: list[dict]):
        self._responses = responses
        self.calls: list[dict] = []

    def execute(self, query: str, variables: dict) -> dict:
        self.calls.append({"query": query, "variables": variables})
        return self._responses.pop(0)


class FailingLinearClient:
    def execute(self, query: str, variables: dict) -> dict:
        raise RuntimeError("network unavailable")
