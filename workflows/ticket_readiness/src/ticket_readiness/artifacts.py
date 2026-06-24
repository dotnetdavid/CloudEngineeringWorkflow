from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ticket_readiness.errors import TicketReadinessError
from ticket_readiness.logging import log_event
from ticket_readiness.security import redact_secrets

_RUN_DIRECTORIES = ("inputs", "inputs/issues", "reports", "drafts", "approvals")


class ArtifactWriteError(TicketReadinessError):
    """Raised when local run evidence cannot be written safely."""


@dataclass(frozen=True)
class RunArtifacts:
    run_id: str
    root: Path

    def path(self, *parts: str) -> Path:
        return _contained_path(self.root, *parts)

    def append_event(
        self,
        *,
        event_type: str,
        state: str,
        message: str,
        issue_id: str | None = None,
        now: datetime | None = None,
    ) -> None:
        event = {
            "timestamp": _timestamp(now),
            "run_id": self.run_id,
            "event_type": event_type,
            "state": state,
            "message": message,
        }
        if issue_id is not None:
            event["issue_id"] = issue_id

        try:
            with self.path("events.jsonl").open("a", encoding="utf-8") as event_file:
                event_file.write(json.dumps(event, sort_keys=True))
                event_file.write("\n")
            log_event(
                event_type=event_type,
                state=state,
                message=message,
                run_id=self.run_id,
                issue_id=issue_id,
                severity="error" if state == "failed" else "info",
            )
        except OSError as exc:
            raise ArtifactWriteError(f"Failed to append run event: {self.run_id}") from exc

    def write_json(self, relative_path: str, payload: dict[str, Any]) -> Path:
        output_path = self.path(relative_path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(redact_secrets(payload), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise ArtifactWriteError(f"Failed to write artifact: {relative_path}") from exc
        return output_path


class ArtifactStore:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def create_run(
        self,
        *,
        workflow_name: str,
        workflow_version: str,
        source: str,
        linear_project_id: str,
        linear_project_url: str,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> RunArtifacts:
        run_id = generate_run_id(source, now=now, nonce=nonce)
        run_root = _contained_path(self._root, run_id)
        staged_root = _contained_path(self._root, f".{run_id}.creating-{uuid.uuid4().hex[:8]}")

        try:
            self._root.mkdir(parents=True, exist_ok=True)
            staged_root.mkdir()
            for directory in _RUN_DIRECTORIES:
                _contained_path(staged_root, directory).mkdir(parents=True, exist_ok=True)
            _contained_path(staged_root, "events.jsonl").touch(exist_ok=False)
            manifest = _manifest(
                run_id=run_id,
                workflow_name=workflow_name,
                workflow_version=workflow_version,
                source=source,
                linear_project_id=linear_project_id,
                linear_project_url=linear_project_url,
                started_at=_timestamp(now),
            )
            _contained_path(staged_root, "manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            staged_root.rename(run_root)
        except OSError as exc:
            if staged_root.exists():
                shutil.rmtree(staged_root, ignore_errors=True)
            raise ArtifactWriteError(f"Failed to create run artifacts: {run_id}") from exc

        return RunArtifacts(run_id=run_id, root=run_root)


def generate_run_id(source: str, *, now: datetime | None = None, nonce: str | None = None) -> str:
    timestamp = _run_timestamp(now)
    source_slug = _slug(source) or "run"
    suffix = _slug(nonce or uuid.uuid4().hex[:8])[:16]
    return f"{timestamp}-{source_slug}-{suffix}"


def _manifest(
    *,
    run_id: str,
    workflow_name: str,
    workflow_version: str,
    source: str,
    linear_project_id: str,
    linear_project_url: str,
    started_at: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "workflow_name": workflow_name,
        "workflow_version": workflow_version,
        "started_at": started_at,
        "completed_at": None,
        "status": "running",
        "source": source,
        "linear_project_id": linear_project_id,
        "linear_project_url": linear_project_url,
        "issue_ids": [],
        "artifact_paths": {
            "inputs": "inputs",
            "input_issues": "inputs/issues",
            "reports": "reports",
            "drafts": "drafts",
            "approvals": "approvals",
            "events": "events.jsonl",
            "manifest": "manifest.json",
        },
        "counts": {},
        "errors": [],
    }


def _contained_path(root: Path, *parts: str) -> Path:
    root_path = root.resolve(strict=False)
    candidate = root_path.joinpath(*parts).resolve(strict=False)
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise ArtifactWriteError(f"Artifact path escapes root: {candidate}") from exc
    return candidate


def _run_timestamp(now: datetime | None) -> str:
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    return timestamp.strftime("%Y-%m-%dT%H%M%SZ")


def _timestamp(now: datetime | None) -> str:
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    return timestamp.isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    return slug.strip("-")
