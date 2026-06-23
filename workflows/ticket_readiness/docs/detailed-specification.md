# Ticket Readiness Workflow Detailed Specification

## Document Control

- Workflow: Ticket Readiness
- Artifact store:
  `/mnt/f/Obsidian/Hermes/projects/CloudEngineerWorkflows/workflows/ticket_readiness`
- Current Linear sandbox project:
  `AI Workflow Sandbox - Ticket Readiness`
- Linear project ID: `8ff212c4-dfc7-4152-88e0-3dd65723a420`
- Linear team: `Asgard AI Agency`
- Implementation repository: separate repository under
  `/mnt/f/Obsidian/Hermes/projects/CloudEngineerWorkflows`
- V1 runtime/language: Python CLI application
- V1 test runner: pytest
- V1 LLM provider: OpenAI API directly
- Date: 2026-06-22
- Status: Draft specification for implementation planning

## 1. Objective

Build a simple durable workflow that evaluates Linear issues for cloud
infrastructure ticket readiness and produces local reports plus approved
write-back drafts.

The system must demonstrate practical AI workflow engineering:

- External tool integration with Linear.
- Durable run artifacts.
- Deterministic checks.
- LLM-assisted interpretation.
- Human approval gates.
- Explicit security and operational guardrails.
- Testable workflow state transitions.

## 2. Product Scope

### 2.1 In Scope For V1

- Read issues from the configured Linear sandbox project.
- Snapshot issue inputs into a timestamped run folder.
- Evaluate issues against a readiness rubric.
- Classify issue work type.
- Classify risk level.
- Produce Markdown readiness reports.
- Produce JSON readiness reports.
- Produce draft Linear comments.
- Record append-only workflow events.
- Record run metadata in a manifest.
- Support human approval records.
- Post approved Linear comments only when explicitly approved.
- Provide local CLI or script entry points for running the workflow.
- Use the OpenAI API directly for V1 LLM-assisted analysis.

### 2.2 Out Of Scope For V1

- Automatic Linear status changes.
- Automatic issue description rewrites.
- Automatic assignment or priority changes.
- Scheduled runs.
- Database persistence.
- AWS API access.
- Terraform execution.
- Production infrastructure mutation.
- Slack or email notifications.
- Multi-workspace Linear support.
- Jira support or Jira connector design.
- Real employer, customer, production, or proprietary work tickets.
- Multi-provider LLM abstraction.
- Advanced authentication management beyond the existing Codex/Linear connector
  or a safely configured future API key.

### 2.3 Non-Negotiable Safety Boundaries

- No secrets may be written to run artifacts.
- No external write-back may happen without human approval.
- If analysis fails, comment posting must not occur.
- If approval state is missing or invalid, comment posting must not occur.
- Only synthetic sandbox tickets may be processed in V1.
- Real production, employer, customer, or proprietary tickets require an
  approved redaction policy before any issue body is stored in synced Obsidian
  folders.

## 3. Primary Use Cases

### 3.1 Backlog Grooming

An engineer runs the workflow against a Linear project before backlog grooming.
The workflow identifies tickets that are ready, tickets needing clarification,
and tickets blocked by missing ownership, approval, or operational context.

### 3.2 Sprint Planning Prep

A technical lead runs the workflow before sprint planning. The run summary
groups issues by readiness, risk, and next action so planning time is spent on
decisions rather than rediscovering missing information.

### 3.3 Code Review Prep

For issues that reference infrastructure changes or PR review, the workflow
identifies missing review inputs such as Terraform plan output, rollback notes,
maintenance window expectations, and owner approval.

### 3.4 Meeting Planning

The workflow produces concise summaries and grooming questions for planning
meetings, reducing manual preparation.

### 3.5 Learning And Portfolio Demonstration

The project demonstrates durable AI workflow concepts relevant to cloud
engineering roles: state, artifacts, tool use, approval gates, risk
classification, and operational evidence.

## 4. Actors

### 4.1 Operator

The person running the workflow. Usually a cloud engineer, platform engineer,
or technical lead.

### 4.2 Approver

The person who approves, rejects, or skips proposed Linear comments. In V1 this
may be the same person as the operator.

### 4.3 Linear Workspace

The external issue source and optional write-back target.

### 4.4 LLM Provider

The model used for issue interpretation and draft generation. The LLM is an
analysis component, not an authority.

## 5. Source Data

### 5.1 Linear Project Configuration

The workflow reads project configuration from:

`config/linear-sandbox.yaml`

Required fields:

- `workspace`
- `team`
- `team_key`
- `project.name`
- `project.id`
- `project.url`
- `write_back.enabled`
- `write_back.requires_human_approval`

### 5.2 Linear Issue Fields

For each issue, the workflow should capture:

- Issue identifier, such as `ASG-40`
- Linear internal ID if available
- Title
- Description
- URL
- Priority
- Estimate
- Status
- Status type
- Labels
- Project ID and name
- Team ID and name
- Created timestamp
- Updated timestamp
- Creator
- Comments, when supported by the implementation phase

### 5.3 Seed Issues

The current sandbox seed set is:

- `ASG-40` Add S3 VPC endpoint for private artifact bucket access
- `ASG-41` Fix production latency
- `ASG-42` Rotate EKS cluster admin access for platform team
- `ASG-43` Review unexpected NAT Gateway cost increase
- `ASG-44` Create Terraform module for standard CloudWatch alarms
- `ASG-45` Prepare sprint planning notes for sandbox network hardening
- `ASG-46` Review Terraform PR for RDS parameter group change
- `ASG-47` Investigate Terraform drift on sandbox IAM role
- `ASG-48` Update README with sandbox deploy command

## 6. Workflow Lifecycle

### 6.1 State Model

Each run should move through explicit states:

```text
initialized
  -> config_loaded
  -> linear_project_read
  -> issue_inputs_snapshotted
  -> deterministic_checks_completed
  -> llm_analysis_completed
  -> reports_written
  -> drafts_written
  -> awaiting_approval
  -> writeback_completed or writeback_skipped
  -> finalized
```

Failure states:

```text
config_failed
linear_read_failed
snapshot_failed
deterministic_checks_failed
llm_analysis_failed
report_write_failed
draft_write_failed
approval_invalid
writeback_failed
finalize_failed
```

### 6.2 Required State Transition Rules

- A run cannot analyze issues before input snapshots are written.
- A run cannot generate reports before deterministic checks complete.
- A run cannot generate drafts before reports are available.
- A run cannot post comments before approval records exist.
- A run cannot finalize as successful if any approved write-back failed.
- A partial run must still write an event log and failure summary when possible.

## 7. Artifact Layout

Each run must create a timestamped folder:

```text
runs/
  2026-06-22T180000Z-asgard-sandbox/
    manifest.json
    events.jsonl
    summary.md
    inputs/
      linear-project.json
      issues/
        ASG-40.json
        ASG-41.json
    reports/
      ASG-40-readiness.md
      ASG-40-readiness.json
    drafts/
      ASG-40-linear-comment.md
    approvals/
      ASG-40-approval.json
```

### 7.1 Manifest Contract

`manifest.json` must include:

- `run_id`
- `workflow_name`
- `workflow_version`
- `started_at`
- `completed_at`
- `status`
- `source`
- `linear_project_id`
- `linear_project_url`
- `issue_ids`
- `artifact_paths`
- `counts`
- `errors`

### 7.2 Event Log Contract

`events.jsonl` must be append-only. Each event must include:

- `timestamp`
- `run_id`
- `event_type`
- `state`
- `issue_id`, when issue-specific
- `message`
- `details`, when needed

### 7.3 Markdown Report Contract

Each Markdown readiness report must include:

- Issue title and source URL
- Readiness verdict
- Score
- Work type
- Risk level
- Summary
- Evidence from ticket
- Missing information
- Grooming questions
- Operational risk
- Security notes
- Suggested acceptance criteria improvements
- Recommended next action
- Link or relative path to draft comment

### 7.4 JSON Report Contract

Each JSON report must include machine-readable fields:

- `issue_id`
- `issue_title`
- `issue_url`
- `readiness_status`
- `readiness_score`
- `work_type`
- `risk_level`
- `dimension_scores`
- `missing_information`
- `grooming_questions`
- `operational_risk`
- `security_notes`
- `acceptance_criteria_improvements`
- `recommended_next_action`
- `evidence`
- `model_metadata`, if LLM analysis is used

### 7.5 Draft Comment Contract

Each draft Linear comment must include:

- Readiness status
- Short explanation
- Missing information
- Grooming questions
- Risk notes
- Recommendation
- Clear marker that the comment was generated by the workflow

### 7.6 Approval Contract

Each approval record must include:

- `issue_id`
- `draft_path`
- `draft_sha256`
- `decision`: `approved`, `rejected`, or `skipped`
- `approved_by`, if available
- `decided_at`
- `rationale`, optional
- `posted_comment_id`, after successful write-back

## 8. Readiness Evaluation

### 8.1 Supported Readiness Statuses

- `ready`
- `needs_grooming`
- `blocked`
- `not_ready`

### 8.2 Required Dimensions

The workflow must evaluate:

- Outcome clarity
- Scope and boundaries
- Environment and blast radius
- Acceptance criteria
- Rollback and recovery
- Security impact
- Observability and validation
- Dependencies and ownership
- Estimate confidence

### 8.3 Work Type Classification

Initial work types:

- `infrastructure_change`
- `incident_or_operational_investigation`
- `access_or_security_change`
- `cost_review`
- `terraform_module`
- `planning`
- `code_review_prep`
- `drift_investigation`
- `documentation`
- `unknown`

### 8.4 Risk Classification

Risk levels:

- `low`
- `medium`
- `high`

High-risk signals:

- Production impact
- IAM or privileged access
- EKS admin access
- Database reboot or data-path change
- Security group or network access change
- Broad policy or broad route impact
- Missing rollback for infrastructure mutation

Medium-risk signals:

- Cost anomaly
- Terraform drift
- VPC endpoint or route table change in sandbox
- Observability module changes

Low-risk signals:

- Documentation-only work
- Planning-only work
- Clearly scoped sandbox-only changes with rollback notes

## 9. Deterministic Checks

The deterministic checker must inspect issue text and metadata for explicit
signals before LLM interpretation.

Required checks:

- Title exists.
- Description exists.
- Priority exists.
- Estimate exists.
- Acceptance criteria section or equivalent bullets exist.
- Environment/account/region/service context exists when relevant.
- Rollback/recovery exists for infrastructure changes.
- Security review signal exists for IAM, access, networking, or production.
- Validation signal exists.
- Missing-input sections are recognized.
- Planning-only and documentation-only tickets are treated with lighter
  requirements.

The deterministic checker must emit structured findings. It must not make final
readiness decisions alone unless the issue is trivially incomplete, such as a
title with no useful description.

## 10. LLM-Assisted Analysis

### 10.1 Purpose

The LLM analysis step interprets issue intent, summarizes evidence, identifies
missing context, drafts grooming questions, and proposes a concise comment.

V1 uses the OpenAI API directly. A provider abstraction is intentionally out of
scope until the workflow contract is proven.

### 10.2 Constraints

The LLM must:

- Use only the provided issue snapshot and rubric.
- Separate evidence from inference.
- Avoid claiming facts not present in the ticket.
- Preserve uncertainty.
- Avoid writing secrets or credentials.
- Avoid recommending direct infrastructure mutation.
- Produce structured output validated by the workflow.

### 10.3 Required LLM Output

The model output must include:

- `summary`
- `work_type`
- `risk_level`
- `readiness_status`
- `missing_information`
- `grooming_questions`
- `operational_risk`
- `security_notes`
- `acceptance_criteria_improvements`
- `recommended_next_action`
- `draft_comment`

### 10.4 Validation

The workflow must validate model output before writing reports:

- Required fields are present.
- Lists are arrays or renderable lists.
- Readiness status is one of the supported values.
- Risk level is one of the supported values.
- Draft comment is non-empty.
- Draft comment does not contain obvious secret-like strings.

Invalid model output must produce a failure event and no Linear write-back.

### 10.5 Provider Decision

V1 should use OpenAI directly rather than Codex-only tooling or a generalized
multi-provider abstraction.

Rationale:

- Direct API usage is easier to demonstrate, test, and explain in an engineering
  portfolio.
- Provider abstraction adds complexity before the workflow contract is proven.
- The workflow can still isolate model calls behind a small internal adapter so
  future provider changes do not contaminate the rest of the codebase.

## 11. Linear Integration

### 11.1 Read Behavior

The workflow must read issues from the configured project ID. It should avoid
workspace-wide reads unless explicitly requested.

### 11.2 Write Behavior

V1 write-back is limited to creating Linear comments from approved drafts.

Disallowed write operations:

- Status changes
- Priority changes
- Assignment changes
- Description rewrites
- Label mutations
- Project moves

### 11.3 Approval Enforcement

Before posting a comment, the workflow must verify:

- A matching approval record exists.
- The approval decision is `approved`.
- The draft hash matches the current draft file.
- The target issue ID matches the approved issue ID.
- The run has not already posted that draft.

## 12. CLI Or Script Interface

The first implementation should expose a simple local command interface.

V1 should be implemented as a Python CLI application. Tests should use pytest.
Document-generation libraries such as `python-docx` are optional and should be
introduced only when a story explicitly requires document output beyond
Markdown, JSON, or plain text artifacts.

V1 approval is manual and file-based. The workflow may generate approval record
templates, but the operator approves, rejects, or skips each draft by editing or
creating approval JSON under the run's `approvals/` directory.

Required commands or modes:

```text
run-analysis
validate-approvals
post-approved
summarize-run
```

Expected usage shape:

```text
ticket-readiness run-analysis --project-config config/linear-sandbox.yaml
ticket-readiness validate-approvals --run RUN_ID
ticket-readiness post-approved --run RUN_ID
ticket-readiness summarize-run --run RUN_ID
```

Exact command names may change during implementation, but these capabilities
must exist.

## 13. Error Handling

### 13.1 Linear Read Failure

- Write failure event.
- Write run summary if possible.
- Do not analyze stale or partial data unless explicitly marked partial.

### 13.2 LLM Failure

- Preserve snapshots and deterministic findings.
- Mark affected issue as analysis failed.
- Do not generate approved comments from failed analysis.

### 13.3 Filesystem Failure

- Fail closed.
- Do not post comments if local evidence cannot be written.

### 13.4 Approval Failure

- If approval record is malformed, reject write-back for that issue.
- If draft hash changed after approval, require reapproval.

### 13.5 Linear Write Failure

- Record failure event.
- Preserve approval record.
- Do not retry indefinitely.
- Make retry a deliberate operator action.

## 14. Observability

V1 observability is file-based.

Required:

- `events.jsonl` for every run.
- Summary counts by readiness status.
- Summary counts by risk level.
- Per-issue error reporting.
- Manifest status.

Nice to have:

- Duration per workflow phase.
- Model token usage and latency, if available.
- Linear API request counts, if available.

## 15. Security Requirements

- Never write API keys, OAuth tokens, cookies, or credentials to artifacts.
- Read the OpenAI API key from a local environment variable or approved local
  secret store; never hard-code it and never persist it in workflow artifacts.
- Redact secret-like strings from issue snapshots and model outputs.
- Do not evaluate real production, employer, customer, or proprietary tickets in
  V1.
- Do not use real work tickets until an explicit redaction threshold and policy
  are approved.
- Treat IAM, networking, database, production, and access changes as elevated
  risk.
- Preserve human approval evidence for every write-back.
- Do not allow LLM output to select target issue IDs for write-back. Target IDs
  must come from trusted workflow state.

## 16. Testing Requirements

### 16.1 Unit Tests

Required unit tests:

- Config loading.
- Run ID generation.
- Artifact path generation.
- Deterministic readiness checks.
- Risk flag detection.
- Readiness status validation.
- Draft hash generation.
- Approval record validation.
- Secret-like string redaction.

### 16.2 Fixture Tests

Use the sandbox issue set as fixtures:

- Ready-ish infrastructure ticket: `ASG-40`
- Vague production ticket: `ASG-41`
- Access/security ticket: `ASG-42`
- Cost review ticket: `ASG-43`
- Terraform module ticket: `ASG-44`
- Planning ticket: `ASG-45`
- Code-review-prep ticket: `ASG-46`
- Drift investigation ticket: `ASG-47`
- Documentation-only ticket: `ASG-48`

### 16.3 Workflow Tests

Required workflow tests:

- Full read-to-report run using mocked Linear data.
- Failed Linear read produces no comments.
- Failed report write produces no comments.
- Missing approval produces no comments.
- Approved draft posts only when hash matches.
- Changed draft after approval requires reapproval.

### 16.4 Manual Acceptance Test

Run against the Asgard sandbox project and verify:

- A timestamped run folder is created.
- Issue snapshots are written.
- Reports are written.
- Draft comments are written.
- No Linear comment is posted before approval.
- Approved comment posting works for one selected test issue.
- Run summary records the result.

## 17. Documentation Requirements

The implementation must include:

- README for local setup.
- Configuration instructions.
- How to run analysis.
- How to approve or reject drafts.
- How to post approved comments.
- Run artifact explanation.
- Safety and redaction notes.
- Known limitations.
- Troubleshooting guide.

## 18. Implementation Work Breakdown

The following work items are suitable for Linear ticket creation.

### 18.1 Project Scaffold

Create a separate implementation repository under
`/mnt/f/Obsidian/Hermes/projects/CloudEngineerWorkflows`, then add the project
structure, Python dependency management, basic CLI entry point, pytest setup,
and local configuration loading.

Acceptance criteria:

- Repository exists outside `agent-foundations`.
- Repository is structured as a Python CLI project.
- Project can be installed or run locally.
- CLI help works.
- Config file can be loaded.
- Pytest can be run.

### 18.2 Linear Read Adapter

Implement a Linear adapter that reads issues from the configured project.

Acceptance criteria:

- Adapter reads issues by project ID.
- Adapter returns normalized issue objects.
- Adapter can run against mocked data in tests.
- Adapter does not perform write operations.

### 18.3 Artifact Store

Implement timestamped run folder creation and artifact writing.

Acceptance criteria:

- Run IDs are stable and collision-resistant.
- Manifest is written.
- Events are appended to `events.jsonl`.
- Inputs, reports, drafts, and approvals directories are created.

### 18.4 Deterministic Readiness Engine

Implement rule-based readiness checks and risk flag detection.

Acceptance criteria:

- Required dimensions are evaluated.
- Findings are structured.
- Fixture issues produce expected obvious findings.
- Rules are covered by unit tests.

### 18.5 LLM Analysis Adapter

Implement model prompting and structured output validation.

Acceptance criteria:

- Prompt uses issue snapshot and rubric only.
- Output schema is validated.
- Invalid output fails closed.
- Model metadata is recorded when available.

### 18.6 Report Generator

Generate Markdown and JSON readiness reports.

Acceptance criteria:

- Markdown reports follow the template.
- JSON reports follow the contract.
- Reports include deterministic and LLM findings.
- Reports are linked from run summary.

### 18.7 Draft Comment Generator

Generate draft Linear comments from validated analysis.

Acceptance criteria:

- Drafts are written to `drafts/`.
- Drafts include readiness status, missing information, questions, risks, and
  recommendation.
- Draft hashes can be computed for approval.

### 18.8 Approval Workflow

Implement manual file-based approval record creation and validation.

Acceptance criteria:

- Workflow documents how an operator manually approves, rejects, or skips a
  draft by writing an approval JSON record.
- Workflow can validate manually edited approval records.
- Approval records include draft hash.
- Changed drafts require reapproval.
- Missing approvals block write-back.

### 18.9 Linear Comment Write-Back

Post approved draft comments to Linear.

Acceptance criteria:

- Only approved drafts are posted.
- Draft hash must match approval record.
- Posted comment ID is recorded.
- Failures are logged without infinite retry.

### 18.10 Run Summary

Generate a human-readable run summary.

Acceptance criteria:

- Summary groups issues by readiness status.
- Summary groups issues by risk level.
- Summary lists errors and skipped write-backs.
- Summary links reports and drafts.

### 18.11 Security And Redaction

Add secret-like string detection and redaction.

Acceptance criteria:

- Obvious API keys and tokens are redacted from artifacts.
- Redaction tests cover common secret patterns.
- Security limitations are documented.

### 18.12 Documentation And Demo

Document usage and demonstrate the workflow against the sandbox project.

Acceptance criteria:

- README explains setup and commands.
- Demo run produces artifacts.
- One approved comment can be posted to a sandbox issue.
- Known risks and limitations are documented.

## 19. Acceptance Criteria For V1

V1 is complete when:

- The workflow can read the sandbox Linear project.
- The workflow can evaluate all seeded issues.
- A run folder is created with manifest, events, inputs, reports, drafts, and
  summary.
- Readiness reports are useful enough for grooming discussion.
- Draft Linear comments are generated.
- No comments post without approval.
- At least one approved draft can be posted to Linear.
- Tests cover core safety and artifact behavior.
- Documentation explains operation, risks, and limitations.

## 20. Resolved Implementation Decisions

- The first implementation should live in its own repository under
  `/mnt/f/Obsidian/Hermes/projects/CloudEngineerWorkflows`.
- V1 should be implemented as a Python CLI application with pytest tests.
- V1 should use the OpenAI API directly for LLM-assisted analysis.
- V1 approval should be manual and file-based.
- Jira support is not part of V1 design or implementation.
- Real work tickets are not authorized for V1. The workflow is limited to
  synthetic sandbox tickets until an explicit redaction threshold and policy are
  approved.
