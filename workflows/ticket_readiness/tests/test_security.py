from __future__ import annotations

import json

from ticket_readiness.artifacts import ArtifactStore
from ticket_readiness.security import contains_secret_like_value, redact_secrets


def test_redact_secrets_covers_common_token_patterns():
    openai_key = "sk" + "-proj-" + "a" * 40
    aws_access_key = "AKIA" + "A" * 16
    text = """
    OpenAI key {openai_key}
    AWS access key {aws_access_key}
    bearer token Bearer abcdefghijklmnopqrstuvwxyz1234567890
    generic api_key=abcdefghijklmnopqrstuvwxyz1234567890
    """.format(openai_key=openai_key, aws_access_key=aws_access_key)

    redacted = redact_secrets(text)

    assert "sk" + "-proj-" not in redacted
    assert aws_access_key not in redacted
    assert "Bearer abcdef" not in redacted
    assert "api_key=abcdefghijklmnopqrstuvwxyz" not in redacted
    assert redacted.count("[REDACTED_SECRET]") >= 4


def test_contains_secret_like_value_detects_nested_payloads():
    payload = {
        "issue": {
            "description": "token: abcdefghijklmnopqrstuvwxyz1234567890",
            "safe": "normal ticket text",
        }
    }

    assert contains_secret_like_value(payload)
    assert not contains_secret_like_value({"safe": ["normal ticket text"]})


def test_artifact_json_writes_redact_secret_like_strings(tmp_path):
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )

    run.write_json(
        "inputs/issues/ASG-40.json",
        {"description": "Use key " + ("sk" + "-proj-" + "a" * 40)},
    )

    payload = json.loads(run.path("inputs/issues/ASG-40.json").read_text(encoding="utf-8"))
    assert payload["description"] == "Use key [REDACTED_SECRET]"
