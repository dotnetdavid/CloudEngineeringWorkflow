from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from ticket_readiness.artifacts import ArtifactStore, ArtifactWriteError, generate_run_id


def test_generate_run_id_is_safe_and_collision_resistant():
    now = datetime(2026, 6, 22, 18, 0, tzinfo=UTC)

    first = generate_run_id("Asgard Sandbox", now=now, nonce="aaaabbbb")
    second = generate_run_id("../Asgard Sandbox", now=now, nonce="ccccdddd")

    assert first == "2026-06-22T180000Z-asgard-sandbox-aaaabbbb"
    assert second == "2026-06-22T180000Z-asgard-sandbox-ccccdddd"
    assert first != second
    assert ".." not in second


def test_create_run_writes_manifest_and_directories(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    now = datetime(2026, 6, 22, 18, 0, tzinfo=UTC)

    run = store.create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        now=now,
        nonce="aaaabbbb",
    )

    assert run.run_id == "2026-06-22T180000Z-asgard-sandbox-aaaabbbb"
    assert run.path("inputs").is_dir()
    assert run.path("inputs", "issues").is_dir()
    assert run.path("reports").is_dir()
    assert run.path("drafts").is_dir()
    assert run.path("approvals").is_dir()

    manifest = json.loads(run.path("manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == run.run_id
    assert manifest["status"] == "running"
    assert manifest["linear_project_id"] == "project-123"
    assert manifest["artifact_paths"]["reports"] == "reports"


def test_append_event_writes_jsonl_records(tmp_path):
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )

    run.append_event(
        event_type="linear_project_read",
        state="succeeded",
        message="Read 2 issues.",
        issue_id="ASG-49",
    )

    lines = run.path("events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["run_id"] == run.run_id
    assert event["event_type"] == "linear_project_read"
    assert event["issue_id"] == "ASG-49"


def test_run_path_rejects_traversal(tmp_path):
    run = ArtifactStore(tmp_path / "runs").create_run(
        workflow_name="ticket-readiness",
        workflow_version="0.1.0",
        source="asgard-sandbox",
        linear_project_id="project-123",
        linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
        nonce="aaaabbbb",
    )

    with pytest.raises(ArtifactWriteError):
        run.path("..", "escape.json")


def test_create_run_fails_closed_when_root_cannot_be_created(tmp_path):
    root = tmp_path / "runs"
    root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ArtifactWriteError):
        ArtifactStore(root).create_run(
            workflow_name="ticket-readiness",
            workflow_version="0.1.0",
            source="asgard-sandbox",
            linear_project_id="project-123",
            linear_project_url="https://linear.app/asgard-ai-agency/project/project-123",
            nonce="aaaabbbb",
        )
