from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request

from ticket_readiness.approvals import write_approval_template
from ticket_readiness.artifacts import ArtifactStore
from ticket_readiness.cli import main


PROJECT_ID = "8ff212c4-dfc7-4152-88e0-3dd65723a420"


def test_integration_strategy_is_documented():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "High-Fidelity Mocked Integration Tests" in readme
    assert "No live Linear or OpenAI mutation is required" in readme


def test_high_fidelity_mocked_read_to_report_flow(tmp_path, monkeypatch):
    config = _config(tmp_path)
    requests = []

    def fake_urlopen(request: Request, timeout: int):
        payload = json.loads(request.data.decode("utf-8"))
        requests.append(
            {
                "authorization": request.get_header("Authorization"),
                "payload": payload,
                "timeout": timeout,
            }
        )
        query = payload.get("query", "")
        if "TicketReadinessProjectIssues" in query:
            return FakeResponse(
                {
                    "data": {
                        "project": {
                            "issues": {
                                "nodes": [_linear_issue_payload()],
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                            }
                        }
                    }
                }
            )
        return FakeResponse(
            {
                "id": "resp_integration_123",
                "model": "gpt-5-mini",
                "output_text": json.dumps(_model_output()),
                "usage": {"input_tokens": 120, "output_tokens": 80, "total_tokens": 200},
                "latency_ms": 512,
            }
        )

    monkeypatch.setenv("LINEAR_API_KEY", "linear-test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    exit_code = main(["--config", str(config), "run-analysis"])

    assert exit_code == 0
    assert [request["payload"]["variables"].get("projectId") for request in requests if "variables" in request["payload"]] == [
        PROJECT_ID
    ]
    assert any(request["payload"].get("model") == "gpt-5-mini" for request in requests)

    run = next((tmp_path / "runs").iterdir())
    report = json.loads((run / "reports" / "ASG-40-readiness.json").read_text(encoding="utf-8"))
    summary = (run / "summary.md").read_text(encoding="utf-8")
    draft = (run / "drafts" / "ASG-40-linear-comment.md").read_text(encoding="utf-8")

    assert report["issue_id"] == "ASG-40"
    assert report["model_metadata"]["response_id"] == "resp_integration_123"
    assert "ASG-40 Add S3 VPC endpoint" in summary
    assert "Please confirm the target route tables." in draft


def test_high_fidelity_mocked_approved_writeback_does_not_mutate_issue_fields(tmp_path, monkeypatch):
    config = _config(tmp_path, write_back_enabled=True)
    run = _approved_run(tmp_path)
    captured = {}

    def fake_urlopen(request: Request, timeout: int):
        payload = json.loads(request.data.decode("utf-8"))
        captured["payload"] = payload
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "data": {
                    "commentCreate": {
                        "success": True,
                        "comment": {
                            "id": "comment-safe-sandbox-123",
                            "url": "https://linear.app/asgard-ai-agency/issue/ASG-40#comment-safe-sandbox-123",
                        },
                    }
                }
            }
        )

    monkeypatch.setenv("LINEAR_API_KEY", "linear-test-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    exit_code = main(["--config", str(config), "post-approved", "--run", run.run_id, "--issue-id", "ASG-40"])

    assert exit_code == 0
    assert captured["authorization"] == "linear-test-key"
    assert captured["payload"]["variables"] == {
        "issueId": "ASG-40",
        "body": "draft comment\n",
    }
    query = captured["payload"]["query"]
    assert "commentCreate" in query
    assert "issueUpdate" not in query
    assert "status" not in query.lower()
    assert "priority" not in query.lower()
    assert "description" not in query.lower()

    approval = json.loads(run.path("approvals", "ASG-40-approval.json").read_text(encoding="utf-8"))
    assert approval["posted_comment_id"] == "comment-safe-sandbox-123"


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _config(tmp_path: Path, *, write_back_enabled: bool = False) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(
        "\n".join(
            [
                "workspace: Asgard AI Agency",
                "team: Asgard AI Agency",
                "team_key: ASG",
                "artifact_root: runs",
                "max_issues: 5",
                "openai:",
                "  model: gpt-5-mini",
                "project:",
                "  name: AI Workflow Sandbox - Ticket Readiness",
                f"  id: {PROJECT_ID}",
                "  url: https://linear.app/asgard-ai-agency/project/ai-workflow-sandbox-ticket-readiness",
                "write_back:",
                f"  enabled: {str(write_back_enabled).lower()}",
                "  requires_human_approval: true",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _approved_run(tmp_path: Path):
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id=PROJECT_ID,
        linear_project_url="https://linear.app/asgard-ai-agency/project/ai-workflow-sandbox-ticket-readiness",
        nonce="aaaabbbb",
    )
    draft_path = "drafts/ASG-40-linear-comment.md"
    run.path(draft_path).write_text("draft comment\n", encoding="utf-8")
    template = write_approval_template(run=run, issue_id="ASG-40", draft_relative_path=draft_path)
    approval_path = run.path(template.path)
    payload = json.loads(approval_path.read_text(encoding="utf-8"))
    payload["decision"] = "approved"
    payload["approved_by"] = "Dave"
    payload["approved_at"] = "2026-06-25T02:00:00Z"
    approval_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run


def _linear_issue_payload() -> dict:
    return {
        "id": "9e47e394-b9aa-4a4d-b769-41f4dce2fabc",
        "identifier": "ASG-40",
        "title": "Add S3 VPC endpoint",
        "description": (
            "Create a VPC endpoint so private workers can reach S3. "
            "Acceptance Criteria: endpoint exists. Validation: verify S3 access. "
            "Rollback: revert Terraform. Security: no public ingress."
        ),
        "url": "https://linear.app/asgard-ai-agency/issue/ASG-40/add-s3-vpc-endpoint",
        "priority": {"value": 2, "name": "High"},
        "estimate": 3,
        "state": {"name": "Todo", "type": "unstarted"},
        "labels": {"nodes": [{"name": "infra"}]},
        "project": {"id": PROJECT_ID, "name": "AI Workflow Sandbox - Ticket Readiness"},
        "team": {"id": "b578eff2-753f-4777-995a-d542d7c2b6f4", "name": "Asgard AI Agency", "key": "ASG"},
        "createdAt": "2026-06-24T18:00:00.000Z",
        "updatedAt": "2026-06-25T02:00:00.000Z",
        "creator": {"id": "8ecdacd4-2f1b-4596-b822-07804a946cf5", "name": "Dave", "email": "dave@example.com"},
    }


def _model_output() -> dict:
    return {
        "summary": "Ticket is ready after confirming route table ownership.",
        "work_type": "infrastructure_change",
        "risk_level": "medium",
        "readiness_status": "needs_grooming",
        "missing_information": ["Route table owner is not explicit."],
        "grooming_questions": ["Who owns the affected route tables?"],
        "operational_risk": ["Endpoint routing can affect private worker access."],
        "security_notes": ["No public ingress is requested."],
        "acceptance_criteria_improvements": ["Name the target route tables."],
        "recommended_next_action": "Confirm ownership before sprint commitment.",
        "draft_comment": "Please confirm the target route tables.",
    }
