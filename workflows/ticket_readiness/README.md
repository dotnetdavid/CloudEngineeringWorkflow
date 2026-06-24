# Ticket Readiness Workflow

The Ticket Readiness workflow evaluates Linear issues before sprint commitment.
It is designed for cloud infrastructure work where ambiguity, missing rollback
plans, unclear ownership, and hidden operational risk can turn small tickets
into expensive surprises.

## Current Sandbox

- Linear workspace: Asgard AI Agency
- Linear team: Asgard AI Agency
- Linear project: AI Workflow Sandbox - Ticket Readiness
- Linear project URL:
  https://linear.app/asgard-ai-agency/project/ai-workflow-sandbox-ticket-readiness-2b4d38343dc1
- Linear project ID: `8ff212c4-dfc7-4152-88e0-3dd65723a420`

## Planning Documents

- `docs/cover-sheet.md` - business and operator-facing overview.
- `docs/detailed-specification.md` - implementation specification intended to
  drive Linear development tickets.
- `docs/workflow-design.md` - early design notes.
- `docs/readiness-rubric.md` - readiness scoring and classification rubric.
- `docs/known-risks.md` - current known risks and safety concerns.

## Build Control

- `build-control/BUILD_RUNBOOK.md` - local planning authority, dependency graph,
  validation gates, non-goals, and Linear creation policy.
- `build-control/build-manifest.yaml` - machine-readable story list,
  dependencies, priorities, and source traces.
- `build-control/stories/` - story files to review before Linear issue
  creation.

## Workflow Shape

```text
read Linear project
  -> snapshot issue inputs
  -> run deterministic readiness checks
  -> run LLM-assisted interpretation
  -> generate local reports
  -> generate draft Linear comments
  -> wait for human approval
  -> optionally post approved comments
  -> archive run evidence
```

## V1 Boundaries

In scope:

- Read issues from the sandbox Linear project.
- Evaluate issue readiness using deterministic checks plus optional
  OpenAI-assisted analysis.
- Write redacted local run artifacts, including input snapshots, reports,
  draft comments, approval records, event logs, and summaries.
- Generate draft Linear comments for human review.
- Validate manual approval records before any write-back.
- Post approved comments back to Linear when write-back is enabled and
  approval is current.
- Keep credentials out of source control, YAML config, and workflow artifacts.

Out of scope:

- Real employer, customer, proprietary, or production ticket processing.
- Autonomous or unsupervised Linear write-back.
- Linear status, priority, assignee, label, project, or description mutation.
- Jira support.
- Hosted services, databases, dashboards, queues, schedulers, or production
  deployments.
- Full data loss prevention; redaction is best-effort for obvious secret-like
  values.
- Credential storage in configuration files or committed artifacts.

## Local Setup

Run commands from this workflow directory:

```bash
cd workflows/ticket_readiness
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

Configure live API credentials as environment variables. The application reads
the OpenAI API key from `OPENAI_API_KEY`; it does not read the key from the YAML
config file.

Linux, macOS, or WSL:

```bash
export OPENAI_API_KEY=<set-in-your-shell>
export LINEAR_API_KEY=<set-in-your-shell>
```

PowerShell:

```powershell
$env:OPENAI_API_KEY = Read-Host "OpenAI API key"
$env:LINEAR_API_KEY = Read-Host "Linear API key"
```

## Run Tests

```bash
.venv/bin/python -m pytest
```

Pytest is configured to use `--capture=sys` because file-descriptor capture is
unreliable from this WSL-mounted project path.

## CLI

Fixture mode runs without external API calls:

```bash
.venv/bin/ticket-readiness --config config/linear-sandbox.yaml run-analysis --fixture-data fixtures/demo-issues.json --mock-llm
```

Live sandbox mode reads the configured Linear project and calls OpenAI:

```bash
export LINEAR_API_KEY=...
export OPENAI_API_KEY=...
.venv/bin/ticket-readiness --config config/linear-sandbox.yaml run-analysis
```

The command prints the run ID. Artifacts are written under `runs/<run-id>/` by
default, or under `artifact_root` when configured.

## API Guardrails

Live runs use two configuration guardrails before calling external APIs:

- `max_issues` caps the number of issues allowed in a run. If a fixture or
  Linear project exceeds this value, the workflow fails before issue artifacts
  or OpenAI calls are written.
- `api_rate_limit.min_interval_seconds` adds a fixed delay before Linear and
  OpenAI HTTP calls. Set it to `0` only for local tests or explicitly approved
  sandbox runs.

HTTP 429 responses from Linear or OpenAI are reported as rate-limit failures.
OpenAI per-issue rate-limit failures are recorded in `events.jsonl` and
`summary.md` for review.

## Run Artifacts

Each run folder should contain:

- `manifest.json` - run metadata, source project, issue identifiers, and status.
- `events.jsonl` - append-only event stream for workflow state transitions.
- `summary.md` - Obsidian-friendly run summary.
- `inputs/` - redacted Linear snapshots used by the run.
- `reports/` - human and machine-readable readiness evaluations.
- `drafts/` - proposed Linear comments awaiting approval.
- `approvals/` - approval, rejection, or skipped-write records.

## Secret Handling

Do not commit API tokens, `.env` files, or generated artifacts containing
sensitive ticket content. Credentials must come from environment variables, a
local secret manager, or an explicitly approved runtime mechanism added in a
later story.

For live Linear reads, the adapter expects `LINEAR_API_KEY` in the process
environment. The key is not stored in config files or emitted to artifacts.

For live OpenAI-assisted analysis, the adapter reads `OPENAI_API_KEY` from the
process environment. Do not place this value in `config/`, run artifacts,
reports, drafts, approvals, or committed files.

V1 is sandbox-only. Do not run this workflow against real production, employer,
customer, or proprietary tickets until a formal data-handling and redaction
policy is approved. The built-in redaction catches obvious token and API key
patterns; it is not a full data loss prevention system.

## Manual Approval Records

Draft comments are not posted automatically. To approve, reject, or skip a
draft, edit the matching `approvals/<issue-id>-approval.json` file after
reviewing the draft. A valid write-back approval requires `decision` to be
`approved`, the `issue_id` to match the workflow issue, and `draft_sha256` to
match the current draft file. Any changed draft requires reapproval.

Validate approvals:

```bash
.venv/bin/ticket-readiness --config config/linear-sandbox.yaml validate-approvals --run <run-id>
```

Post one approved sandbox comment:

```bash
.venv/bin/ticket-readiness --config config/linear-sandbox.yaml post-approved --run <run-id> --issue-id ASG-40
```

Write-back is comment-only. The workflow does not change status, priority,
assignee, description, labels, or project membership.

## Troubleshooting

- `LINEAR_API_KEY is required`: set `LINEAR_API_KEY` or run fixture mode.
- `OPENAI_API_KEY is required`: set `OPENAI_API_KEY` or use `--mock-llm` with
  fixture data.
- `Approval record is not approved`: review the draft and manually set
  `decision` to `approved`.
- `Approval record is stale`: the draft changed after approval; review and
  approve again.
- `pytest` capture errors on mounted paths: this project configures
  `--capture=sys` to avoid file-descriptor capture issues seen on the mounted
  workspace.

## Current Status

TR-001 through TR-012 are implemented for a sandbox V1 workflow. The tool can
run from fixture data without external calls, or run live against the configured
sandbox Linear project when credentials are supplied.
