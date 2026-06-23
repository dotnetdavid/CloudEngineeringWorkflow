# Cloud Engineer Workflows

This folder holds learning projects and future practical workflow projects for
cloud infrastructure engineering.

The initial pattern is a file-backed artifact store: workflow runs write inputs,
events, reports, drafts, approvals, and summaries to disk before any external
system is updated. This keeps early experiments durable and auditable without
adding database overhead before the workflow shape is proven.

## Workflows

- `workflows/ticket_readiness/` - evaluates Linear issues for sprint readiness,
  missing context, operational risk, security concerns, and approval needs.

## Frameworks

- `frameworks/story-definition-framework.md` - consolidated story creation
  framework with entry criteria, exit criteria, story template, validation
  rules, and Linear creation policy.

## Safety Rules

- Do not store secrets, credentials, API tokens, or private keys here.
- Treat synced Obsidian content as potentially shared unless proven otherwise.
- Redact sensitive real-world data before storing issue bodies, account IDs,
  hostnames, IAM policies, incident details, or customer information.
- External write-back must be human-approved. Linear is not a side-effect sink.

## Artifact Pattern

Each workflow run should create a timestamped folder under that workflow's
`runs/` directory:

```text
runs/
  2026-06-22T180000Z-asgard-sandbox/
    manifest.json
    events.jsonl
    summary.md
    inputs/
    reports/
    drafts/
    approvals/
```
