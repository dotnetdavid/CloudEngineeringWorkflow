from __future__ import annotations

from io import BytesIO
import urllib.error

import pytest

from ticket_readiness.llm_analysis import (
    HTTPOpenAIClient,
    LLMAnalysisAdapter,
    LLMAnalysisError,
    build_analysis_prompt,
    validate_model_output,
)
from ticket_readiness.linear import LinearIssue, LinearPriority
from ticket_readiness.readiness import evaluate_issue


def test_prompt_uses_only_issue_snapshot_rubric_and_deterministic_findings():
    issue = _issue()
    findings = evaluate_issue(issue)
    rubric = {"statuses": {"ready": {}, "needs_grooming": {}, "blocked": {}, "not_ready": {}}}

    prompt = build_analysis_prompt(issue=issue, rubric=rubric, deterministic_result=findings)

    assert "Issue Snapshot" in prompt
    assert "Readiness Rubric" in prompt
    assert "Deterministic Findings" in prompt
    assert issue.title in prompt
    assert "Linear API" not in prompt
    assert "OPENAI_API_KEY" not in prompt


def test_validate_model_output_accepts_required_schema():
    output = _valid_output()

    result = validate_model_output(output)

    assert result.summary == "Ticket is mostly clear but needs one owner confirmation."
    assert result.risk_level == "medium"
    assert result.readiness_status == "needs_grooming"
    assert result.model_metadata == {}


def test_validate_model_output_fails_closed_for_invalid_status():
    output = _valid_output(readiness_status="ship_it_anyway")

    with pytest.raises(LLMAnalysisError, match="Unsupported readiness_status"):
        validate_model_output(output)


def test_validate_model_output_fails_closed_for_secret_like_comment():
    output = _valid_output(draft_comment="Use key " + _fake_openai_key())

    with pytest.raises(LLMAnalysisError, match="secret-like"):
        validate_model_output(output)


def _fake_openai_key() -> str:
    return "sk" + "-proj-" + "a" * 40


def test_adapter_records_model_metadata_from_mock_client():
    client = FakeOpenAIClient(
        {
            "output_text": _valid_output_json(),
            "id": "resp_123",
            "model": "gpt-5-mini",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
    )
    adapter = LLMAnalysisAdapter(client=client, model="gpt-5-mini")

    result = adapter.analyze(
        issue=_issue(),
        rubric={"statuses": {"ready": {}, "needs_grooming": {}, "blocked": {}, "not_ready": {}}},
        deterministic_result=evaluate_issue(_issue()),
    )

    assert result.model_metadata["response_id"] == "resp_123"
    assert result.model_metadata["model"] == "gpt-5-mini"
    assert result.model_metadata["usage"] == {"input_tokens": 100, "output_tokens": 50}
    assert client.calls[0]["model"] == "gpt-5-mini"
    assert client.calls[0]["text"]["format"]["type"] == "json_schema"


def test_http_openai_client_reads_api_key_from_environment(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"output_text": "{}"}'

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    HTTPOpenAIClient(api_key=None, timeout_seconds=12).create_response(
        model="gpt-5-mini",
        input=[],
    )

    assert captured["authorization"] == "Bearer test-openai-key"
    assert captured["timeout"] == 12


def test_http_openai_client_throttles_before_request(monkeypatch):
    limiter = FakeRateLimiter()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"output_text": "{}"}'

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: FakeResponse())

    HTTPOpenAIClient(api_key="openai-key", rate_limiter=limiter).create_response(
        model="gpt-5-mini",
        input=[],
    )

    assert limiter.calls == 1


def test_http_openai_client_reports_rate_limit(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            hdrs={},
            fp=BytesIO(b'{"error":"slow down"}'),
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(LLMAnalysisError, match="rate limited"):
        HTTPOpenAIClient(api_key="openai-key").create_response(model="gpt-5-mini", input=[])


def _issue() -> LinearIssue:
    return LinearIssue(
        identifier="ASG-40",
        title="Add S3 VPC endpoint for private artifact bucket access",
        description="Acceptance Criteria: endpoint exists. Validation: verify S3 access.",
        priority=LinearPriority(value=2, name="High"),
        estimate=3,
        url="https://linear.app/asgard-ai-agency/issue/ASG-40/example",
    )


def _valid_output(**overrides):
    output = {
        "summary": "Ticket is mostly clear but needs one owner confirmation.",
        "work_type": "infrastructure_change",
        "risk_level": "medium",
        "readiness_status": "needs_grooming",
        "missing_information": ["Owner is not explicit."],
        "grooming_questions": ["Who owns the route table update?"],
        "operational_risk": ["Route table changes can affect private subnet egress."],
        "security_notes": ["No public ingress is requested."],
        "acceptance_criteria_improvements": ["Name the target route tables."],
        "recommended_next_action": "Clarify owner and route table scope before sprint commitment.",
        "draft_comment": "This looks close. Please clarify the owner and target route tables.",
    }
    output.update(overrides)
    return output


def _valid_output_json() -> str:
    import json

    return json.dumps(_valid_output())


class FakeOpenAIClient:
    def __init__(self, response: dict):
        self._response = response
        self.calls: list[dict] = []

    def create_response(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class FakeRateLimiter:
    def __init__(self):
        self.calls = 0

    def wait(self) -> None:
        self.calls += 1
